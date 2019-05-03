## Copyright 2017 Knossos authors, see NOTICE file
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

from __future__ import absolute_import, print_function

import sys
import logging
import threading
import six

from . import uhf
uhf(__name__)

from . import center
from .qt import QtCore

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
    busy = False

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

            if not task[0].background:
                self.busy = True

            if center.raven:
                center.raven.context.activate()

            try:
                reset()
                set_callback(task[0]._track_progress)
                task[0]._init()
                task[0].work(*task[1])
            except SystemExit:
                self.busy = False
                return
            except Exception:
                logging.exception('Exception in Thread!')

            try:
                task[0]._deinit()
            except Exception:
                logging.exception('Exception in Thread!')

            if center.raven:
                center.raven.context.clear()

            self.busy = False


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

        self._stop_workers = False
        self._workers = []
        self._tasks = []

    def _get_work(self):
        while True:
            if self._stop_workers:
                return None

            with self._tasks_lock:
                # Only run one task at once to avoid problems caused by multiple tasks modifying
                # the installed mods repo.
                if self._tasks:
                    work = self._tasks[0]._get_work()
                    if work is not None:
                        return work

            # No work here... let's wait for more.
            with self._worker_cond:
                self._worker_cond.wait()

    def add_task(self, task):
        if not task._has_work():
            logging.warning('Added an empty task of type "%s". Ignoring it!', task.__class__.__name__)

            # Make sure it finishes.
            task._done.set()
            task.done.emit()
            return

        with self._tasks_lock:
            self._tasks.append(task)
            task._master = self
            task._attached = True

        task.done.connect(self.check_tasks)

        with self._worker_cond:
            self._worker_cond.notify_all()

    def check_tasks(self):
        with self._tasks_lock:
            for task in self._tasks[:]:
                if not task._has_work():
                    self._tasks.remove(task)
                    task._attached = False

                    # There are still tasks left. Tell the workers to start them.
                    if self._tasks:
                        self.wake_workers()

    def wake_workers(self):
        with self._worker_cond:
            self._worker_cond.notify_all()

    def is_busy(self):
        return any([w.busy for w in self._workers])


class Task(QtCore.QObject):
    _results = None
    _result_lock = None
    _work = None
    _work_count = 0
    _res_count = 0
    _work_lock = None
    _done = None
    _master = None
    _attached = False
    _progress = None
    _progress_lock = None
    _running = 0
    _pending = 0
    _threads = 0
    _local = None
    _slot_prog = None
    _thread_prog = None
    background = False
    can_abort = True
    aborted = False
    title = None
    mods = None
    done = QtCore.Signal()
    progress = QtCore.Signal(tuple)

    def __init__(self, work=None, threads=0):
        super(Task, self).__init__()

        if work is None:
            work = []

        self._results = []
        self._work = work
        self._work_count = len(work)
        self._result_lock = threading.Lock()
        self._work_lock = threading.Lock()
        self._done = threading.Event()
        self._progress_lock = threading.Lock()
        self._threads = threads
        self._local = threading.local()
        self._thread_prog = {}
        self.mods = []

    def _get_work(self):
        with self._work_lock:
            if len(self._work) == 0:
                return None
            elif self._threads > 0 and self._running >= self._threads:
                return None
            else:
                self._pending += 1
                return (self, (self._work.pop(0),))

    def _has_work(self):
        with self._work_lock:
            return len(self._work) > 0

    def _init(self):
        with self._progress_lock:
            self._running += 1

    def _deinit(self):
        with self._progress_lock:
            with self._work_lock:
                self._pending -= 1

            self._running -= 1
            self._res_count += 1

            if self._running == 0 and not self._has_work():
                if self._done.is_set():
                    logging.warn('%s finished more than once!' % self.__class__.__name__)
                else:
                    self._done.set()
                    self.done.emit()

    def _track_progress(self, prog, text):
        with self._progress_lock:
            if self._slot_prog:
                if hasattr(self._local, 'slot'):
                    self._slot_prog[self._local.slot] = (self._slot_prog[self._local.slot][0], prog, text)

                total = 0
                for label, prog, text in self._slot_prog.values():
                    total += prog

                self.progress.emit((total / max(1, len(self._slot_prog)), self._slot_prog, self.title))
            else:
                if self._work_count == 1:
                    self.progress.emit((prog, {}, self.title))
                else:
                    self.progress.emit((self._res_count / self._work_count, {}, self.title))

    def post(self, result):
        with self._result_lock:
            self._results.append(result)

    def add_work(self, work):
        if len(work) == 0:
            # If self._work is empty after we're done, it will trip the empty task detection in add_task
            # which will cause us to finish too early. The easiest way to avoid this is to never call add_work()
            # with an empty list. Which is why we report this as an error.
            logging.error('add_work() was passed an empty list! (%s)' % self.__class__.__name__)
            return

        with self._work_lock:
            self._work.extend(work)
            self._work_count = max(self._work_count, len(self._work))

        if self._master is not None:
            if not self._attached:
                self._master.add_task(self)
            else:
                self._master.wake_workers()

    def abort(self):
        if not self.can_abort:
            logging.debug("Abort request failed for task %s because it can't abort!" % self)
            return False

        # Empty the work queue, this won't stop running workers but it will
        # stop calls to the work() method.
        with self._work_lock:
            self._work = []
            self.aborted = True

        self._master.check_tasks()

    def get_progress(self):
        with self._work_lock:
            wc_left = len(self._work)
            wc_total = self._work_count
            pending = self._pending

        count = float(wc_total)
        if count == 0:
            count = 0.00001
            total = 1
        else:
            total = (wc_total - wc_left - pending) / count

        for item in prog.values():
            total += item[0] * (1.0 / count)

        return total, {}, self.title

    def is_done(self):
        if not self._done.is_set():
            with self._progress_lock:
                if self._running == 0 and not self._has_work():
                    self._done.set()

        return self._done.is_set()

    def get_results(self):
        if not self._done.is_set():
            self._done.wait()

        with self._result_lock:
            return self._results


class MultistepTask(Task):
    _steps = None
    _sdone = False
    _cur_step = -1

    def __init__(self, steps=None, **kwargs):
        super(MultistepTask, self).__init__(**kwargs)

        if steps is None:
            steps = self._steps

        if isinstance(steps, int):
            snum = steps
            steps = []
            for i in range(1, snum + 1):
                steps.append((getattr(self, 'init' + str(i)), getattr(self, 'work' + str(i))))

        self._steps = steps

    def _has_work(self):
        return not self._sdone and not self.aborted

    def _get_work(self):
        with self._work_lock:
            if (self._threads > 0 and self._pending >= self._threads) or self._sdone or self.aborted:
                return None
            elif len(self._work) == 0 or self._cur_step < 0:
                if self._pending == 0 and self._running == 0:
                    self._pending += 1
                    return (self, ('MAGIC_MULTITASK_STEP_KEY_###',))
                else:
                    return None
            else:
                self._pending += 1
                return (self, (self._work.pop(0),))

    def work(self, arg):
        if self.aborted:
            logging.error('Work triggered on aborted task!!!')
            return

        # Any better ideas for this magic key?
        if arg == 'MAGIC_MULTITASK_STEP_KEY_###':
            # Maybe we need to advance to the next step.
            self._work_lock.acquire()

            # Just to make sure (the lock might have caused a short delay)
            if self.aborted:
                logging.warning('Task aborted during step switch!')
                self._work_lock.release()
                return

            if (self._pending == 1 and self._running == 1 and len(self._work) == 0) or self._cur_step < 0:
                self._work_lock.release()
                self._next_step()
            else:
                # TODO: This still happens on Windows and Mac OS. For some reason it doesn't happen on Linux...
                logging.warning('Either we still have some work to do (unlikely) or there are still some other threads running (%d).', self._running)
                self._work_lock.release()

            return

        # Call the current work method
        self._steps[self._cur_step][1](arg)

    def _next_step(self):
        if self.aborted:
            return

        self._cur_step += 1
        logging.debug('Entering step %d of %d in task %s.', self._cur_step + 1, len(self._steps), self.__class__.__name__)

        if self._cur_step >= len(self._steps):
            # That was the last one.
            self._sdone = True
            return

        # Call the init routine.
        self._done.set()
        self._steps[self._cur_step][0]()
        self._done.clear()

        with self._result_lock:
            self._results = []

        # Wake all free workers.
        self._master.wake_workers()
