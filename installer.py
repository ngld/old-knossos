import sys


# Redirect sys.stdout and sys.stderr
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
import subprocess
import time
import progress
from qt import QtCore, QtGui
from ui.main import Ui_MainWindow
from ui.progress import Ui_Dialog as Ui_Progress
from ui.modinfo import Ui_Dialog as Ui_Modinfo
from fs2mod import ModInfo2
from util import get

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')

main_win = None
progress_win = None
pmaster = progress.Master()
settings = {
    'fs2_bin': None,
    'fs2_path': None,
    'mods': None,
    'installed_mods': None
}
settings_path = os.path.expanduser('~/.fs2mod-py/settings.pick')


def init_ui(ui, win):
    ui.setupUi(win)
    for attr in ui.__dict__:
        setattr(win, attr, getattr(ui, attr))

    return win


# This wrapper makes sure that the wrapped function is always run in the QT main thread.
def run_in_qt(func):
    signal = SignalContainer()
    
    def dispatcher(*args):
        signal.signal.emit(args)
    
    def listener(params):
        func(*params)
    
    signal.signal.connect(listener)
    
    return dispatcher


class SignalContainer(QtCore.QObject):
    signal = QtCore.Signal(list)


# Tasks
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
        
        for mod in data.values():
            if 'logo' in mod:
                mod['logo'] = get(os.path.dirname(link) + '/' + mod['logo']).read()
        
        self.post(data)
    
    def finish(self):
        global settings
        
        settings['mods'] = {}
        
        for part in self.get_results():
            settings['mods'].update(part)
        
        save_settings()
        update_list()


class InstallTask(progress.Task):
    def __init__(self, mods):
        super(InstallTask, self).__init__()
        
        self.done.connect(self.finish)
        self.add_work([('install', modname, None) for modname in mods])
    
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


class UninstallTask(progress.Task):
    def __init__(self, mods):
        super(UninstallTask, self).__init__()
        
        self.done.connect(self.finish)
        self.add_work(mods)
    
    def work(self, modname):
        mod = ModInfo2(settings['mods'][modname])
        mod.remove(settings['fs2_path'])
    
    def finish(self):
        update_list()


# Progress display
class ProgressDisplay(object):
    win = None
    _threads = None
    _tasks = None
    _log_lines = None
    log_len = 50
    
    def __init__(self):
        self._threads = []
        self._tasks = []
        self._log_lines = []
        
        self.win = init_ui(Ui_Progress(), QtGui.QDialog(main_win))
        self.win.setModal(True)
    
    def show(self):
        self.win.show()
        progress.reset()
        
        progress.set_callback(self.update_prog)
        progress.update(0, 'Working...')
        
        sys.stdout.callback = self.show_line
        sys.stderr.callback = self.show_line
    
    def update_prog(self, percent, text):
        self.win.progressBar.setValue(percent * 100)
        self.win.label.setText(text)
    
    def update_tasks(self):
        total = 0
        count = len(self._tasks)
        items = {}
        layout = self.win.tasks.layout()
        
        for task in self._tasks:
            t_total, t_items = task.get_progress()
            total += t_total / count
            items.update(t_items)
        
        while len(self._threads) < len(items):
            bar = QtGui.QProgressBar()
            bar.setValue(0)
            label = QtGui.QLabel()
            
            layout.addWidget(label)
            layout.addWidget(bar)
            self._threads.append((label, bar))
        
        while len(self._threads) > len(items):
            label, bar = self._threads.pop()
            
            label.destroy()
            bar.destroy()
        
        for i, item in enumerate(items.values()):
            label, bar = self._threads[i]
            label.setText(item[1])
            bar.setValue(item[0] * 100)
        
        self.win.progressBar.setValue(total * 100)
    
    @run_in_qt
    def show_line(self, data):
        data = data.split('\n')
        if len(self._log_lines) == 0:
            self._log_lines = data
        else:
            self._log_lines[-1] += data.pop(0)
            self._log_lines.extend(data)
        
        # Limit the amount of visible lines
        if len(self._log_lines) > self.log_len:
            self._log_lines = self._log_lines[len(self._log_lines) - self.log_len:]
        
        data = '\n'.join(self._log_lines).replace('<', '&lt;').replace('\n', '<br>').replace(' ', '&nbsp;')
        self.win.textEdit.setHtml('<html><head><style type="text/css">body { background-color: #000000; }</style></head><body>' +
                                  '<span style="color: #B2B2B2; font-family: \'DejaVu Sans Mono\', monospace;">' + data + '</span></body></html>')
        scroller = self.win.textEdit.verticalScrollBar()
        scroller.setValue(scroller.maximum())
    
    def hide(self):
        progress.set_callback(None)
        sys.stdout.callback = None
        sys.stderr.callback = None
        
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
            self.hide()


def run_task(task):
    progress_win.add_task(task)
    pmaster.add_task(task)


# FS2 tab
def save_settings():
    with open(settings_path, 'wb') as stream:
        pickle.dump(settings, stream)


def init_fs2_tab():
    global settings, main_win
    
    if settings['fs2_path'] is not None:
        if not os.path.isfile(os.path.join(settings['fs2_path'], settings['fs2_bin'])):
            QtGui.QMessageBox.warning(main_win, 'Warning', 'I somehow couldn\'t find your FS2 binary (%s). Please select it again!' % (settings['fs2_bin']))
            
            settings['fs2_bin'] = None
            select_fs2_path()
            return
    
    if settings['fs2_path'] is None:
        # Disable mod tab if we don't know where fs2 is.
        main_win.tabs.setTabEnabled(1, False)
        main_win.tabs.setCurrentIndex(0)
        main_win.fs2_bin.hide()
    else:
        main_win.tabs.setTabEnabled(1, True)
        main_win.tabs.setCurrentIndex(1)
        main_win.fs2_bin.show()
        main_win.fs2_bin.setText('Selected FS2 Open: ' + os.path.join(settings['fs2_path'], settings['fs2_bin']))


def do_gog_extract():
    QtGui.QMessageBox.warning(main_win, 'Info', 'Not yet implemented!', QtGui.QMessageBox.Ok)
    pass


def select_fs2_path():
    global settings
    
    if sys.platform[:3] == 'win':
        mask = 'Executable (*.exe)'
    else:
        mask = ''
    
    if settings['fs2_path'] is None:
        path = os.path.expanduser('~')
    else:
        path = settings['fs2_path']
    
    fs2_bin = QtGui.QFileDialog.getOpenFileName(main_win, 'Please select your fs2_open_* file.', path, mask)[0]
    
    if fs2_bin is not None and os.path.isfile(fs2_bin):
        settings['fs2_bin'] = os.path.basename(fs2_bin)
        settings['fs2_path'] = os.path.dirname(fs2_bin)
        
        save_settings()
        init_fs2_tab()


def run_fs2():
    p = subprocess.Popen([os.path.join(settings['fs2_path'], settings['fs2_bin'])], cwd=settings['fs2_path'])
    
    time.sleep(0.3)
    if p.poll() is not None:
        QtGui.QMessageBox.critical(main_win, 'Failed', 'Starting FS2 Open (%s) failed! (return code: %d)' % (os.path.join(settings['fs2_path'], settings['fs2_bin']), p.returncode))


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
    table.setSortingEnabled(False)
    
    row = 0
    for name, mod in settings['mods'].items():
        mod = ModInfo2(mod)
        archives, s, c = mod.check_files(os.path.join(settings['fs2_path'], mod.folder))
        
        name_item = QtGui.QTableWidgetItem(name)
        if s == c:
            name_item.setCheckState(QtCore.Qt.Checked)
            status = 'Installed'
        elif s == 0:
            name_item.setCheckState(QtCore.Qt.Unchecked)
            status = 'Not installed'
        else:
            name_item.setCheckState(QtCore.Qt.PartiallyChecked)
            status = '%d corrupted or updated files' % (c - s)
        
        name_item.setData(QtCore.Qt.UserRole, name_item.checkState())
        version_item = QtGui.QTableWidgetItem(mod.version)
        status_item = QtGui.QTableWidgetItem(status)
        
        table.setItem(row, 0, name_item)
        table.setItem(row, 1, version_item)
        table.setItem(row, 2, status_item)
        
        row += 1
    
    table.setSortingEnabled(True)
    table.resizeColumnsToContents()


def select_mod(row, col):
    name = main_win.tableWidget.item(row, 0).text()
    installed = main_win.tableWidget.item(row, 0).data(QtCore.Qt.UserRole) == QtCore.Qt.Checked
    mod = ModInfo2(settings['mods'][name])
    
    # NOTE: lambdas don't work with connect()
    def do_run():
        if installed:
            run_mod(mod)
        else:
            msg = QtGui.QMessageBox()
            msg.setIcon(QtGui.QMessageBox.Question)
            msg.setText('You don\'t have %s, yet. Shall I install it?' % (mod.name))
            msg.setInformativeText('%s will be installed.' % (mod.name))
            msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            msg.setDefaultButton(QtGui.QMessageBox.Yes)
            
            if msg.exec_() == QtGui.QMessageBox.Yes:
                task = InstallTask([mod.name])
                task.done.connect(do_run2)
                run_task(task)
    
    def do_run2():
        run_mod(mod)
    
    infowin = init_ui(Ui_Modinfo(), QtGui.QDialog(main_win))
    infowin.setModal(True)
    infowin.modname.setText(mod.name + ' - ' + mod.version)
    
    if mod.logo is None:
        infowin.logo.hide()
    else:
        img = QtGui.QPixmap()
        img.loadFromData(mod.logo)
        infowin.logo.setPixmap(img)
    
    infowin.desc.setPlainText(mod.desc)
    infowin.note.setPlainText(mod.note)
    
    infowin.closeButton.clicked.connect(infowin.close)
    infowin.runButton.clicked.connect(do_run)
    infowin.show()


def run_mod(mod):
    modpath = os.path.join(settings['fs2_path'], mod.folder)
    ini = None
    modfolder = None
    
    for item in mod.contents:
        if os.path.basename(item).lower() == 'mod.ini':
            ini = item
            break
    
    if ini is None:
        # Look for the first subdirectory then.
        if mod.folder == '':
            for item in mod.contents:
                if item.lower().endswith('.vp'):
                    modfolder = item.split('/')[0]
                    break
        else:
            modfolder = mod.folder.split('/')[0]
    else:
        primlist = []
        seclist = []
        
        with open(os.path.join(modpath, ini), 'r') as stream:
            for line in stream:
                if line.strip() == '[multimod]':
                    break
            
            for line in stream:
                line = [p.strip(' ;\n\r') for p in line.split('=')]
                if line[0] == 'primarylist':
                    primlist = line[1].split(',')
                elif line[0] == 'secondarylist':
                    seclist = line[1].split(',')
        
        # Build the whole list
        modfolder = ','.join(primlist + [ini.split('/')[0]] + seclist)
    
    # Now look for the user directory...
    if sys.platform in ('linux2', 'linux'):
        # TODO: What about Mac OS ?
        path = os.path.expanduser('~/.fs2_open')
    else:
        path = settings['fs2_path']
    
    path = os.path.join(path, 'data/cmdline_fso.cfg')
    if os.path.exists(path):
        with open(path, 'r') as stream:
            cmdline = stream.read().split(' ')
    else:
        cmdline = []
    
    mod_found = False
    for i, part in enumerate(cmdline):
        if part.strip() == '-mod':
            mod_found = True
            cmdline[i + 1] = modfolder
    
    if not mod_found:
        cmdline.append('-mod')
        cmdline.append(modfolder)
    
    with open(path, 'w') as stream:
        stream.write(' '.join(cmdline))
    
    run_fs2()


def apply_selection():
    global settings
    
    if settings['mods'] is None:
        return
    
    table = main_win.tableWidget
    install = []
    uninstall = []
    
    for row in range(0, table.rowCount()):
        name_item = table.item(row, 0)
        
        if name_item.checkState() == name_item.data(QtCore.Qt.UserRole):
            # Unchanged
            continue
        
        if name_item.checkState():
            # Install
            install.append(name_item.text())
        else:
            # Uninstall
            uninstall.append(name_item.text())
    
    if len(install) == 0 and len(uninstall) == 0:
        QtGui.QMessageBox.warning(main_win, 'Warning', 'You didn\'t change anything! There\'s nothing for me to do...')
        return
    
    if len(install) > 0:
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Question)
        msg.setText('Do you really want to install these mods?')
        msg.setInformativeText(', '.join(install) + ' will be installed.')
        msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        msg.setDefaultButton(QtGui.QMessageBox.Yes)
        
        if msg.exec_() == QtGui.QMessageBox.Yes:
            run_task(InstallTask(install))
    
    if len(uninstall) > 0:
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Question)
        msg.setText('Do you really want to remove these mods?')
        msg.setInformativeText(', '.join(uninstall) + ' will be removed.')
        msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        msg.setDefaultButton(QtGui.QMessageBox.Yes)
        
        if msg.exec_() == QtGui.QMessageBox.Yes:
            run_task(UninstallTask(install))


def main():
    global settings, main_win, progress_win
    
    app = QtGui.QApplication([])
    progress_win = ProgressDisplay()

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

    init_fs2_tab()
    
    main_win.gogextract.clicked.connect(do_gog_extract)
    main_win.select.clicked.connect(select_fs2_path)

    main_win.apply_sel.clicked.connect(apply_selection)
    main_win.update.clicked.connect(fetch_list)
    
    main_win.tableWidget.cellDoubleClicked.connect(select_mod)
    main_win.tableWidget.sortItems(0)
    
    pmaster.start_workers(10)
    QtCore.QTimer.singleShot(300, update_list)
    
    main_win.show()
    app.exec_()

if __name__ == '__main__':
    main()
