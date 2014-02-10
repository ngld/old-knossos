## Copyright 2014 ngld <ngld@tproxy.de>
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

"""
This module is just for taking track of (some kind of) progress.
"""

import sys
import logging
import threading
import six
import util
from qt import QtCore, QtGui
from ui.progress import Ui_Dialog as Ui_Progress

try:
    import curses
except ImportError:
    curses = None

if six.PY2:
    threading.get_ident = lambda: threading.current_thread().ident

_progress = threading.local()


def reset():
    global _progress
    
    _progress.value = 0.0
    _progress.text = ''
    _progress.tasks = []
    _progress.callback = None

# Initialize with empty values.
reset()


# total_progress = off + span * task_progress
# Example: If you're tracking downloads and starting file 3 of 10, call start_task(3/10, 'Downloading whatever (%s)...')
def start_task(off, span, tmpl='%s'):
    if not hasattr(_progress, 'tasks'):
        reset()
    
    _progress.tasks.insert(0, (off, float(span), tmpl))


def finish_task():
    if not hasattr(_progress, 'tasks'):
        reset()
    
    _progress.tasks.pop(0)


def set_callback(cb):
    if not hasattr(_progress, 'tasks'):
        reset()
    
    _progress.callback = cb


def update(prog, text=''):
    global _progress
    
    if not hasattr(_progress, 'tasks'):
        reset()
    
    for task in _progress.tasks:
        prog = task[0] + prog * task[1]
        if '%s' in task[2]:
            text = task[2] % (text,)
        else:
            text = task[2]
    
    _progress.value = prog
    _progress.text = text
    
    if _progress.callback is not None:
        _progress.callback(prog, text)


# Task scheduler
class Worker(threading.Thread):
    def __init__(self, master):
        super(Worker, self).__init__()
        
        self._master = master
        self.daemon = True
        self.start()
    
    def run(self):
        while True:
            task = self._master._get_work()
            if task is None:
                return
            
            try:
                reset()
                set_callback(task[0]._track_progress)
                task[0]._init()
                task[0].work(*task[1])
            except:
                logging.exception('Exception in Thread!')
            
            task[0]._deinit()


class Master(object):
    _tasks = None
    _tasks_lock = None
    _workers = None
    _stop_workers = False
    _worker_cond = None
    
    def __init__(self):
        self._tasks = []
        self._tasks_lock = threading.Lock()
        self._workers = []
        self._worker_cond = threading.Condition()
    
    def start_workers(self, num):
        for n in range(0, num):
            self._workers.append(Worker(self))
    
    def stop_workers(self):
        self._stop_workers = True
        
        with self._worker_cond:
            self._worker_cond.notify_all()
        
        for w in self._workers:
            w.join()
    
    def _get_work(self):
        while True:
            if self._stop_workers:
                return None
            
            with self._tasks_lock:
                while len(self._tasks) > 0:
                    work = self._tasks[0]._get_work()
                    if work is not None:
                        return work
                    else:
                        task = self._tasks.pop(0)
                        task._attached = False
            
            # No work here... let's wait for more.
            with self._worker_cond:
                self._worker_cond.wait()
    
    def add_task(self, task):
        if not task._has_work():
            logging.warning('Added an empty task of type "%s". Ignoring it!', str(task.__class__.__name__))
            return
        
        with self._tasks_lock:
            self._tasks.append(task)
            task._master = self
            task._attached = True
        
        with self._worker_cond:
            self._worker_cond.notify_all()


class Task(QtCore.QObject):
    _results = None
    _result_lock = None
    _work = None
    _work_lock = None
    _done = None
    _master = None
    _attached = False
    _progress = None
    _progress_lock = None
    _running = 0
    done = QtCore.Signal()
    progress = QtCore.Signal()
    
    def __init__(self, work=[]):
        super(Task, self).__init__()
        
        self._results = []
        self._work = work
        self._result_lock = threading.Lock()
        self._work_lock = threading.Lock()
        self._done = threading.Event()
        self._progress = dict()
        self._progress_lock = threading.Lock()
    
    def _get_work(self):
        with self._work_lock:
            if len(self._work) == 0:
                return None
            else:
                return (self, (self._work.pop(0),))
    
    def _has_work(self):
        with self._work_lock:
            return len(self._work) > 0
    
    def _init(self):
        with self._progress_lock:
            self._progress[threading.get_ident()] = (0, 'Ready')
            self._running += 1
    
    def _deinit(self):
        running = 0
        
        with self._progress_lock:
            self._progress[threading.get_ident()] = (1, 'Done')
            self._running -= 1
            running = self._running
        
        if running == 0 and not self._has_work():
            self._done.set()
            self.done.emit()
    
    def _track_progress(self, prog, text):
        with self._progress_lock:
            self._progress[threading.get_ident()] = (prog, text)
        
        self.progress.emit()
    
    def post(self, result):
        with self._result_lock:
            self._results.append(result)
    
    def add_work(self, work):
        with self._work_lock:
            self._work.extend(work)
        
        if not self._attached and self._master is not None:
            self._master.add_task(self)
    
    def get_progress(self):
        with self._progress_lock:
            prog = self._progress.copy()
        
        with self._result_lock:
            results = len(self._results)
        
        with self._work_lock:
            work = len(self._work)
        
        work_count = float(results + work + len(prog))
        if work_count == 0:
            total = 1
        else:
            total = results / work_count
        
        for item in prog.values():
            total += item[0] * (1.0 / work_count)
        
        return total, prog
    
    def is_done(self):
        return self._done.is_set()
    
    def get_results(self):
        if not self._done.is_set():
            self._done.wait()
        
        with self._result_lock:
            return self._results


# Curses display
class Textbox(object):
    win = None
    lock = None
    border = False
    content = []
    
    def __init__(self, win, lock=None):
        self.win = win
        self.lock = lock
    
    def wrap(self, text):
        wrapped = []
        y, x, height, width = self.get_coords()
        
        for line in text.split('\n'):
            while len(line) > width:
                wrapped.append(line[:width])
                line = ' ' + line[width:]
            
            wrapped.append(line)
        
        return wrapped
    
    def get_coords(self):
        height, width = self.win.getmaxyx()
        
        if self.border:
            y = x = 1
            height -= 2
            width -= 2
        else:
            y = x = 0
        
        return y, x, height, width
    
    def appendln(self, text):
        with self.lock:
            text = self.wrap(text)
            y, x, height, width = self.get_coords()
            
            self.content.extend(text)
            while len(self.content) > height:
                self.content.pop(0)
            
            self.win.move(y, x)
            self.win.insdelln(-len(text))
            
            start = y + height - len(text)
            self.win.move(start, x)
            for ly in range(start, start + len(text)):
                self.win.addstr(ly, x, text.pop(0))
            
            self.win.refresh()
    
    def append(self, text):
        with self.lock:
            if len(self.content) == 0:
                self.appendln(text)
                return
            
            text = self.wrap(self.content[-1] + text)
            y, x, height, width = self.get_coords()
            self.content[-1] = text.pop(0)
            
            self.win.addstr(y + height - 1, x, self.content[-1])
            self.appendln('\n'.join(text))
    
    def set_text(self, text):
        with self.lock:
            text = self.wrap(text)
            self.content = text
            
            if self.border:
                self.win.resize(len(text) + 2, self.win.getmaxyx()[1])
            else:
                self.win.resize(len(text), self.win.getmaxyx()[1])
            
            y, x, height, width = self.get_coords()
            
            self.win.erase()
            if self.border:
                self.win.border()
            
            for ly, line in enumerate(text):
                self.win.addstr(y + ly, x, line)
            
            self.win.refresh()


class CursesOutput(object):
    win = None
    log = None
    other_win = None
    lock = None
    
    def __init__(self, win, log=None, other_win=None):
        self.win = win
        self.log = log
        self.other_win = other_win
        self.lock = threading.RLock()
    
    def write(self, data):
        with self.lock:
            self.win.append(data)
            self.other_win.redrawwin()
            
            if self.log is not None:
                self.log.write(data)
    
    def flush(self):
        with self.lock:
            if self.log is not None:
                self.log.flush()


def _init_curses(scr, cb, log):
    # Setup the display
    height, width = scr.getmaxyx()
    clock = threading.RLock()
    statusw = Textbox(curses.newwin(0, 0, 0, 0), clock)
    statusw.border = True
    win = Textbox(scr, clock)
    
    def show_status(prog, text):
        h, w = statusw.win.getmaxyx()
        statusw.set_text('\n [' + '=' * int(prog * (w - 8)) + '>\n' + text)
    
    set_callback(show_status)
    
    stdout = sys.stdout
    stderr = sys.stderr
    sys.stderr = sys.stdout = CursesOutput(win, log, statusw.win)
    handlers = []
    
    # Redirect the logging output.
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            if handler.stream in (stdout, stderr):
                handlers.append((handler, handler.stream))
                handler.stream = sys.stdout
    
    cb()
    
    for handler, stream in handlers:
        handler.stream = stream
    
    sys.stdout = stdout
    sys.stderr = stderr
    set_callback(None)


def init_curses(cb, log=None):
    curses.wrapper(_init_curses, cb, log)


# Qt Display
class ProgressDisplay(object):
    win = None
    _threads = None
    _tasks = None
    _log_lines = None
    log_len = 50
    
    def __init__(self):
        self._task_bars = []
        self._tasks = []
        self._log_lines = []
        
        self.win = util.init_ui(Ui_Progress(), QtGui.QDialog(QtGui.QApplication.activeWindow()))
        self.win.setModal(True)
    
    def show(self):
        reset()
        
        set_callback(self.update_prog)
        update(0, 'Working...')
        self.win.show()
    
    def update_prog(self, percent, text):
        self.win.progressBar.setValue(percent * 100)
        self.win.label.setText(text)
    
    def update_tasks(self):
        total = 0
        count = len(self._tasks)
        items = []
        layout = self.win.tasks.layout()
        
        for task in self._tasks:
            t_total, t_items = task.get_progress()
            total += t_total / count

            for prog, text in t_items.values():
                # Skip 0% and 100% items, they aren't interesting...
                if prog not in (0, 1):
                    items.append((prog, text))
        
        diff = len(self._task_bars) != len(items)
        if diff:
            spacer = layout.itemAt(layout.count() - 1)
        
        while len(self._task_bars) < len(items):
            bar = QtGui.QProgressBar()
            label = QtGui.QLabel()
            
            layout.addWidget(label)
            layout.addWidget(bar)
            self._task_bars.append((label, bar))
        
        while len(self._task_bars) > len(items):
            label, bar = self._task_bars.pop()
            
            label.deleteLater()
            bar.deleteLater()
        
        if diff:
            # Reappend the spacer.
            layout.removeItem(spacer)
            layout.addItem(spacer)
        
        for i, item in enumerate(items):
            label, bar = self._task_bars[i]
            label.setText(item[1])
            bar.setValue(item[0] * 100)
        
        if len(self._task_bars) == 1:
            self.win.progressBar.hide()
        else:
            self.win.progressBar.setValue(total * 100)
            self.win.progressBar.show()
    
    def hide(self):
        set_callback(None)
        self.win.hide()
    
    def add_task(self, task):
        self._tasks.append(task)
        task.done.connect(self._check_tasks)
        task.progress.connect(self.update_tasks)
        
        if not self.win.isVisible():
            self.show()
    
    def _check_tasks(self):
        for task in self._tasks:
            if task.is_done():
                self._tasks.remove(task)
        
        if len(self._tasks) == 0:
            # Cleanup
            self.update_tasks()
            self.hide()
