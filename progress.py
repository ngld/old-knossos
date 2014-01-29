"""
This module is just for taking track of (some kind of) progress.
"""

import threading

cur_progress = 0.0
cur_text = ''
_tasks = []
progress_callback = None


def reset():
    global cur_progress, cur_text, _tasks
    
    cur_progress = 0.0
    cur_text = ''
    _tasks = []

# total_progress = off + span * task_progress
# Example: If you're tracking downloads and starting file 3 of 10, call start_task(3/10, 'Downloading whatever (%s)...')
def start_task(off, span, tmpl):
    _tasks.insert(0, (off, float(span), tmpl))


def finish_task():
    _tasks.pop(0)


def update(prog, text=''):
    global cur_progress, cur_text
    
    for task in _tasks:
        prog = task[0] + prog * task[1]
        if '%s' in task[2]:
            text = task[2] % (text,)
        else:
            text = task[2]
    
    cur_progress = prog
    cur_text = text
    
    if progress_callback is not None:
        progress_callback(prog, text)


# Task scheduler
class Worker(threading.Thread):
    _working = False
    
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
            
            self._working = True
            task[0]._post(task[0].work(*task[1]))
            self._working = False


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
                        self._tasks.pop(0)
            
            # No work here... let's wait for more.
            with self._worker_cond:
                self._worker_cond.wait()
    
    def add_task(self, task):
        with self._tasks_lock:
            self._tasks.append(task)
        
        with self._worker_cond:
            self._worker_cond.notify_all()


class Task(object):
    _results = None
    _result_lock = None
    _work = None
    _work_lock = None
    _done = None
    
    def __init__(self, work=[]):
        self._results = {}
        self._work = work
        self._result_lock = threading.Lock()
        self._work_lock = threading.Lock()
        self._done = threading.Event()
    
    def _get_work(self):
        with self._work_lock:
            if len(self._work) == 0:
                return None
            else:
                return (self, (self._work.pop(0),))
    
    def _post(self, result):
        with self._result_lock:
            self.results.append(result)
        
        if len(self._work) == 0:
            self._done.set()
    
    def add_work(self, work):
        with self._work_lock:
            self._work.extend(work)
    
    def get_results(self):
        with self._done:
            if not self._done.is_set():
                self._done.wait()
        
        with self._result_lock:
            return self._results
