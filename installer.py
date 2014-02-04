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

import os
import logging
import pickle
import json
import subprocess
import time
import progress
import util
import fs2mod
from qt import QtCore, QtGui
from ui.main import Ui_MainWindow
from ui.progress import Ui_Dialog as Ui_Progress
from ui.modinfo import Ui_Dialog as Ui_Modinfo
from fs2mod import ModInfo2

VERSION = '0.1-alpha'

main_win = None
progress_win = None
installed = []
pmaster = progress.Master()
settings = {
    'fs2_bin': None,
    'fs2_path': None,
    'mods': None,
    'installed_mods': None,
    'hash_cache': None
}
settings_path = os.path.expanduser('~/.fs2mod-py')
if sys.platform.startswith('win'):
    settings_path = os.path.expandvars('$APPDATA/fs2mod-py')


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
        data = util.get(link).read().decode('utf8', 'replace')
        
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
                mod['logo'] = util.get(os.path.dirname(link) + '/' + mod['logo']).read()
        
        self.post(data)
    
    def finish(self):
        global settings
        
        settings['mods'] = {}
        
        for part in self.get_results():
            settings['mods'].update(part)
        
        save_settings()
        update_list()


class CheckTask(progress.Task):
    def __init__(self, update=False):
        super(CheckTask, self).__init__()
        
        self.done.connect(self.finish)
        self.add_work(settings['mods'].values())

    def work(self, mod):
        mod = ModInfo2(mod)
        a, s, c, m = mod.check_files(os.path.join(settings['fs2_path'], mod.folder))
        self.post((mod, a, s, c, m))

    def finish(self):
        _update_list(self.get_results())


class InstallTask(progress.Task):
    def __init__(self, mods):
        super(InstallTask, self).__init__()
        
        self.done.connect(self.finish)
        self.add_work([('install', modname, None) for modname in mods])
    
    def work(self, params):
        action, mod, archive = params
        
        if action == 'install':
            mod = ModInfo2(settings['mods'][mod])
            #self.add_work([('install', d, None) for d in mod.dependencies])
            
            if not os.path.exists(os.path.join(settings['fs2_path'], mod.folder)):
                mod.setup(settings['fs2_path'])
            else:
                progress.start_task(0, 1)
                archives, s, c, m = mod.check_files(settings['fs2_path'])
                progress.finish_task()
                
                if len(archives) > 0:
                    self.add_work([('dep', mod, a) for a in archives])
        else:
            progress.start_task(0, 2/3.0)
            
            modpath = os.path.join(settings['fs2_path'], mod.folder)
            mod.download(modpath, set([archive]))
            
            progress.finish_task()
            progress.start_task(2.0/3.0, 0.5/3.0)
            
            mod.extract(modpath, set([archive]))
            progress.finish_task()
            
            progress.start_task(2.5/3.0, 0.5/3.0)
            mod.cleanup(modpath, set([archive]))
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
        mod.remove(os.path.join(settings['fs2_path'], mod.folder))
    
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
        items = []
        layout = self.win.tasks.layout()
        
        for task in self._tasks:
            t_total, t_items = task.get_progress()
            total += t_total / count

            for prog, text in t_items.values():
                # Skip 0% and 100% items, they aren't interesting...
                if prog not in (0, 1):
                    items.append((prog, text))

        while len(self._threads) < len(items):
            bar = QtGui.QProgressBar()
            bar.setValue(0)
            label = QtGui.QLabel()
            
            layout.addWidget(label)
            layout.addWidget(bar)
            self._threads.append((label, bar))
        
        while len(self._threads) > len(items):
            label, bar = self._threads.pop()
            
            label.deleteLater()
            bar.deleteLater()
        
        for i, item in enumerate(items):
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
            # Cleanup
            self.update_tasks()
            self.hide()


def run_task(task):
    progress_win.add_task(task)
    pmaster.add_task(task)


# FS2 tab
def save_settings():
    with open(os.path.join(settings_path, 'settings.pick'), 'wb') as stream:
        pickle.dump(settings, stream)


def init_fs2_tab():
    global settings, main_win
    
    if settings['fs2_path'] is not None:
        if settings['fs2_bin'] is None or not os.path.isfile(os.path.join(settings['fs2_path'], settings['fs2_bin'])):
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
        main_win.fs2_bin.setText('Selected FS2 Open: ' + os.path.normcase(os.path.join(settings['fs2_path'], settings['fs2_bin'])))


def do_gog_extract():
    QtGui.QMessageBox.warning(main_win, 'Info', 'Not yet implemented!', QtGui.QMessageBox.Ok)
    pass


def select_fs2_path():
    global settings
    
    if sys.platform.startswith('win'):
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
    
    time.sleep(0.5)
    if p.poll() is not None:
        QtGui.QMessageBox.critical(main_win, 'Failed', 'Starting FS2 Open (%s) failed! (return code: %d)' % (os.path.join(settings['fs2_path'], settings['fs2_bin']), p.returncode))


# Mod tab
def fetch_list():
    run_task(FetchTask())


def _update_list(results):
    global settings, main_win, installed
    
    installed = []
    rows = dict()
    
    for mod, archives, s, c, m in results:
        if s == c:
            cstate = QtCore.Qt.Checked
            status = 'Installed'
            installed.append(mod.name)
        elif s == 0:
            cstate = QtCore.Qt.Unchecked
            status = 'Not installed'
        else:
            cstate = QtCore.Qt.PartiallyChecked
            status = '%d corrupted or updated files' % (c - s)
        
        row = QtGui.QTreeWidgetItem((mod.name, mod.version, status))
        row.setCheckState(0, cstate)
        row.setData(0, QtCore.Qt.UserRole, cstate)
        row.setData(0, QtCore.Qt.UserRole + 1, m)
        
        rows[mod.name] = (row, mod)
    
    for row, mod in rows.values():
        if mod.parent is None or mod.parent not in rows:
            main_win.modTree.addTopLevelItem(row)
        else:
            rows[mod.parent][0].addChild(row)


def update_list():
    global settings, main_win
    
    main_win.modTree.clear()

    if settings['mods'] is None:
        return

    run_task(CheckTask())


def resolve_dependencies(mods):
    global installed

    needed = mods[:]
    provided = dict()

    while len(needed) > 0:
        mod = settings['mods'][needed.pop(0)]

        for dep in mod['dependencies']:
            dep = (dep + '/mod.ini').lower()
            if not dep in provided:
                for omod in settings['mods'].values():
                    for path in omod['contents']:
                        if (omod['folder'] + '/' + path).lstrip('/').lower().startswith(dep) and omod['name'] != mod['name']:
                            provided[dep] = omod['name']
                            needed.append(omod['name'])

                            break

                    if dep in provided:
                        break

                if dep not in provided:
                    logging.warning('Dependency "%s" of "%s" wasn\'t found!', dep, mod['name'])

    deps = set(provided.values()) - set(mods) - set(installed)
    return list(deps)


def select_mod(item, col):
    name = item.text(0)
    installed = item.data(0, QtCore.Qt.UserRole) == QtCore.Qt.Checked
    check_msgs = item.data(0, QtCore.Qt.UserRole + 1)
    mod = ModInfo2(settings['mods'][name])
    
    # NOTE: lambdas don't work with connect()
    def do_run():
        if installed:
            run_mod(mod)
        else:
            deps = resolve_dependencies([mod.name])

            msg = QtGui.QMessageBox()
            msg.setIcon(QtGui.QMessageBox.Question)
            msg.setText('You don\'t have %s, yet. Shall I install it?' % (mod.name))
            msg.setInformativeText('%s will be installed.' % (', '.join([mod.name] + deps)))
            msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            msg.setDefaultButton(QtGui.QMessageBox.Yes)
            
            if msg.exec_() == QtGui.QMessageBox.Yes:
                task = InstallTask([mod.name] + deps)
                task.done.connect(do_run2)
                run_task(task)
                infowin.close()
    
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

    if len(check_msgs) > 0 and item.data(0, QtCore.Qt.UserRole) != QtCore.Qt.Unchecked:
        infowin.note.appendPlainText('\nCheck messages:\n* ' + '\n* '.join(check_msgs))
    
    infowin.closeButton.clicked.connect(infowin.close)
    infowin.runButton.clicked.connect(do_run)
    infowin.show()


def run_mod(mod):
    modpath = os.path.join(settings['fs2_path'], mod.folder)
    ini = None
    modfolder = None
    
    # Look for the mod.ini
    for item in mod.contents:
        if os.path.basename(item).lower() == 'mod.ini':
            ini = item
            break
    
    if ini is None:
        # No mod.ini found, look for the first subdirectory then.
        if mod.folder == '':
            for item in mod.contents:
                if item.lower().endswith('.vp'):
                    modfolder = item.split('/')[0]
                    break
        else:
            modfolder = mod.folder.split('/')[0]
    else:
        # mod.ini was found, now read its "[multimod]" section.
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
        
        if ini == 'mod.ini':
            ini = mod.folder + '/' + ini

        # Build the whole list for -mod
        modfolder = ','.join(primlist + [ini.split('/')[0]] + seclist).strip(',')
    
    # Now look for the user directory...
    if sys.platform in ('linux2', 'linux'):
        # TODO: What about Mac OS ?
        path = os.path.expanduser('~/.fs2_open')
    else:
        path = settings['fs2_path']
    
    path = os.path.join(path, 'data/cmdline_fso.cfg')
    if os.path.exists(path):
        with open(path, 'r') as stream:
            cmdline = stream.read().strip().split(' ')
    else:
        cmdline = []
    
    mod_found = False
    for i, part in enumerate(cmdline):
        if part.strip() == '-mod':
            mod_found = True
            cmdline[i + 1] = modfolder
            break
    
    if not mod_found:
        cmdline.append('-mod')
        cmdline.append(modfolder)
    
    with open(path, 'w') as stream:
        stream.write(' '.join(cmdline))
    
    run_fs2()


def read_tree(parent, items=[]):
    if isinstance(parent, QtGui.QTreeWidget):
        for i in range(0, parent.topLevelItemCount()):
            item = parent.topLevelItem(i)
            items.append((item, None))
            
            read_tree(item, items)
    else:
        for i in range(0, parent.childCount()):
            item = parent.child(i)
            items.append((item, parent))
            
            read_tree(item, items)
    
    return items


def apply_selection():
    global settings
    
    if settings['mods'] is None:
        return
    
    install = []
    uninstall = []
    items = read_tree(main_win.modTree)
    for item, parent in items:
        if item.checkState(0) == item.data(0, QtCore.Qt.UserRole):
            # Unchanged
            continue
        
        if item.checkState(0):
            # Install
            install.append(item.text(0))
        else:
            # Uninstall
            uninstall.append(item.text(0))
    
    if len(install) == 0 and len(uninstall) == 0:
        QtGui.QMessageBox.warning(main_win, 'Warning', 'You didn\'t change anything! There\'s nothing for me to do...')
        return
    
    if len(install) > 0:
        install = install + resolve_dependencies(install)

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
            run_task(UninstallTask(uninstall))


def main():
    global VERSION, settings, main_win, progress_win
    
    if hasattr(sys, 'frozen'):
        if hasattr(sys, '_MEIPASS'):
            os.chdir(sys._MEIPASS)
        else:
            os.chdir(os.path.dirname(sys.executable))

        if sys.platform.startswith('win') and os.path.isfile('7z.exe'):
            util.SEVEN_PATH = os.path.abspath('7z.exe')
    
    if not os.path.isdir(settings_path):
        os.makedirs(settings_path)
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')
    if sys.platform.startswith('win'):
        # Windows won't display a console so write our log messages to a file.
        logging.getLogger().addHandler(logging.FileHandler(os.path.join(settings_path, 'log.txt')))
    
    # Try to load our settings.
    spath = os.path.join(settings_path, 'settings.pick')
    if os.path.exists(spath):
        try:
            with open(spath, 'rb') as stream:
                settings.update(pickle.load(stream))
        except:
            logging.exception('Failed to load settings from "%s"!', spath)

        save_settings()
    
    if settings['hash_cache'] is not None:
        fs2mod.HASH_CACHE = settings['hash_cache']
    
    app = QtGui.QApplication([])

    if not util.test_7z():
        QtGui.QMessageBox.critical(None, 'Error', 'I can\'t find "7z"! Please install it and run this program again.', QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
        return

    progress_win = ProgressDisplay()
    main_win = init_ui(Ui_MainWindow(), QtGui.QMainWindow())

    if hasattr(sys, 'frozen'):
        # Add note about bundled content.
        # NOTE: This will appear even when this script is bundled with py2exe or a similiar program.
        main_win.aboutLabel.setText(main_win.aboutLabel.text().replace('</body>', '<br><p>' +
                                    'This bundle was created with <a href="http://pyinstaller.org">PyInstaller</a>' +
                                    ' and contains a 7z executable.</p></body>'))
        
        if os.path.isfile('commit'):
            with open('commit', 'r') as data:
                VERSION += '-' + data.read().strip()
    
    tab = main_win.tabs.addTab(QtGui.QWidget(), 'Version: ' + VERSION)
    main_win.tabs.setTabEnabled(tab, False)
    
    init_fs2_tab()
    
    main_win.aboutLabel.linkActivated.connect(QtGui.QDesktopServices.openUrl)
    
    main_win.gogextract.clicked.connect(do_gog_extract)
    main_win.select.clicked.connect(select_fs2_path)

    main_win.apply_sel.clicked.connect(apply_selection)
    main_win.update.clicked.connect(fetch_list)
    
    main_win.modTree.itemClicked.connect(select_mod)
    main_win.modTree.sortItems(0, QtCore.Qt.AscendingOrder)
    main_win.modTree.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
    main_win.modTree.setSortingEnabled(True)
    
    pmaster.start_workers(10)
    QtCore.QTimer.singleShot(300, update_list)

    main_win.show()
    app.exec_()
    
    settings['hash_cache'] = dict()
    for path, info in fs2mod.HASH_CACHE.items():
        # Skip deleted files
        if os.path.exists(path):
            settings['hash_cache'][path] = info
    
    save_settings()

if __name__ == '__main__':
    main()
