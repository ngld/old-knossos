"""
This module is just for taking track of (some kind of) progress.
"""

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
