import sys


# Redirect sys.stdout and sys.stderr!
class UserStream(object):
    _wrapped = None
    callback = None
    
    def __init__(self, wrapped=None):
        self._wrapped = wrapped
    
    def write(self, data):
        if self.callback is not None:
            self.callback(data)
        
        if self._wrapped is not None:
            self._wrapped.write(data)
    
    def flush(self):
        if self._wrapped is not None:
            self._wrapped.flush()

sys.stdout = UserStream(sys.stdout)
sys.stderr = UserStream(sys.stderr)

import os.path
import logging
import pickle
import json
import progress
from qt import QtCore, QtGui
from ui.main import Ui_MainWindow
from ui.progress import Ui_Dialog as Ui_Progress
#from parser import EntryPoint
from fs2mod import ModInfo2
from util import get

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')

main_win = None
progress_win = None
pmaster = progress.Master()
settings = {
    'fs2_path': None,
    'mods': None,
    'installed_mods': None
}
settings_path = os.path.expanduser('~/.fs2mod-py/settings.pick')


class FetchTask(progress.Task):
    def __init__(self):
        super(FetchTask, self).__init__()
        
        self.done.connect(self.finish)
        self.add_work(['http://dev.tproxy.de/fs2/repo.txt'])
    
    def work(self, link):
        data = get(link).read().decode('utf8', 'replace')
        
        try:
            data = json.loads(data)
        except:
            logging.exception('Failed to decode "%s"!', link)
            return
        
        if '#include' in data:
            self.add_work(data['#include'])
            del data['#include']
        
        self.post(data)
    
    def finish(self):
        global settings
        
        settings['mods'] = {}
        
        for part in self.get_results():
            settings['mods'].update(part)
        
        save_settings()
        update_list()


class RepairTask(progress.Task):
    _mod = None
    
    def __init__(self, mod, archives):
        super(RepairTask, self).__init__()
        
        self._mod = mod
        self.add_work(archives)
    
    def work(self, archive):
        pass


class InstallTask(progress.Task):
    def __init__(self, modname):
        super(InstallTask, self).__init__()
        
        self.done.connect(self.finish)
        self.add_work([('install', modname, None)])
    
    def work(self, params):
        action, mod, archive = params
        
        if action == 'install':
            mod = ModInfo2(settings['mods'][mod])
            self.add_work([('install', d, None) for d in mod.dependencies])
            
            if not os.path.exists(os.path.join(settings['fs2_path'], mod.folder)):
                mod.setup(settings['fs2_path'])
            else:
                progress.start_task(0, 1)
                archives, s, c = mod.check_files(settings['fs2_path'])
                progress.finish_task()
                
                if len(archives) > 0:
                    self.add_work([('dep', mod, a) for a in archives])
        else:
            progress.start_task(0, 2/3.0)
            
            modpath = os.path.join(settings['fs2_path'], mod.folder)
            mod.download(modpath, set([archive]))
            
            progress.finish_task()
            progress.start_task(2.0/3.0, 0.5/3.0)
            
            mod.extract(modpath)
            progress.finish_task()
            
            progress.start_task(2.5/3.0, 0.5/3.0)
            mod.cleanup(modpath)
            progress.finish_task()
    
    def finish(self):
        update_list()


def init_ui(ui, win):
    ui.setupUi(win)
    for attr in ui.__dict__:
        setattr(win, attr, getattr(ui, attr))

    return win


def show_progress():
    global progress_win
    
    if progress_win is None:
        progress_win = init_ui(Ui_Progress(), QtGui.QDialog(main_win))
        progress_win.setModal(True)
    
    progress_win.show()
    progress.reset()
    
    def update_prog(percent, text):
        progress_win.progressBar.setValue(percent * 100)
        progress_win.label.setText(text)
    
    def show_line(data):
        progress_win.textEdit.insertPlainText(data)
    
    progress.set_callback(update_prog)
    sys.stdout.callback = show_line
    sys.stderr.callback = show_line


def hide_progress():
    global progress_win
    
    progress_win.hide()


def run_task(task):
    global running_task
    
    def update_task_progress():
        total, items = task.get_progress()
        text = []
        for item in items.values():
            text.append('%3d%% %s' % (item[0] * 100, item[1]))
        
        progress.update(total, '\n'.join(text))
    
    show_progress()
    task.done.connect(hide_progress)
    task.progress.connect(update_task_progress)
    pmaster.add_task(task)


# FS2 tab
def save_settings():
    with open(settings_path, 'wb') as stream:
        pickle.dump(settings, stream)


def do_gog_extract():
    QtGui.QMessageBox.warning(main_win, 'Info', 'Not yet implemented!', QtGui.QMessageBox.Ok)
    pass


def select_fs2_path():
    global settings

    settings['fs2_path'] = QtGui.QFileDialog.getExistingDirectory()

    if settings['fs2_path'] is not None and os.path.isdir(settings['fs2_path']):
        save_settings()
        main_win.tabs.setTabEnabled(1, True)
        main_win.tabs.setCurrentIndex(1)


# Mod tab
def fetch_list():
    run_task(FetchTask())


def update_list():
    global settings, main_win
    
    table = main_win.tableWidget
    if settings['mods'] is None:
        table.setRowCount(0)
        return
    
    table.setRowCount(len(settings['mods']))
    
    row = 0
    for name, mod in settings['mods'].items():
        item = QtGui.QTableWidgetItem(name)
        item.setFlags(QtCore.Qt.ItemIsUserCheckable)
        table.setItem(row, 0, item)
        table.setItem(row, 1, QtGui.QTableWidgetItem(mod['version']))
        table.setItem(row, 2, QtGui.QTableWidgetItem('?'))
        
        row += 1


def select_mod():
    pass


def install_mod():
    pass


def uninstall_mod():
    pass


def main():
    global settings, main_win
    
    app = QtGui.QApplication([])

    main_win = init_ui(Ui_MainWindow(), QtGui.QMainWindow())
    
    # Try to load our settings.
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'rb') as stream:
                settings = pickle.load(stream)
        except:
            logging.exception('Failed to load settings from "%s"!', settings_path)
    else:
        if not os.path.isdir(os.path.dirname(settings_path)):
            os.makedirs(os.path.dirname(settings_path))

        save_settings()

    if settings['fs2_path'] is None:
        # Disable mod tab if we don't know where fs2 is.
        main_win.tabs.setTabEnabled(1, False)
    else:
        main_win.tabs.setCurrentIndex(1)

    main_win.gogextract.clicked.connect(do_gog_extract)
    main_win.select.clicked.connect(select_fs2_path)

    main_win.install_mod.clicked.connect(install_mod)
    main_win.uninstall_mod.clicked.connect(uninstall_mod)
    main_win.select_mod.clicked.connect(select_mod)
    main_win.update.clicked.connect(fetch_list)
    
    pmaster.start_workers(10)
    update_list()
    
    main_win.show()
    app.exec_()

if __name__ == '__main__':
    main()
