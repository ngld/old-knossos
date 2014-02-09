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

import sys
import os
import logging
import pickle
import json
import subprocess
import tempfile
import shutil
import stat
import glob
import time
import progress
import util
import fso_parser
from qt import QtCore, QtGui
from ui.main import Ui_MainWindow
from ui.progress import Ui_Dialog as Ui_Progress
from ui.modinfo import Ui_Dialog as Ui_Modinfo
from ui.gogextract import Ui_Dialog as Ui_Gogextract
from ui.select_list import Ui_Dialog as Ui_SelectList
from fs2mod import ModInfo2

VERSION = '0.1'

main_win = None
progress_win = None
installed = []
shared_files = {}
pmaster = progress.Master()
settings = {
    'fs2_bin': None,
    'fs2_path': None,
    'mods': None,
    'hash_cache': None,
    'repos': [('json', 'http://dev.tproxy.de/fs2/all.json', 'ngld\'s HLP Mirror')],
    'innoextract_link': 'http://dev.tproxy.de/fs2/innoextract.txt'
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
        self.add_work(settings['repos'])
    
    def work(self, link):
        if link[0] == 'json':
            data = util.get(link[1]).read().decode('utf8', 'replace')
            
            try:
                data = json.loads(data)
            except:
                logging.exception('Failed to decode "%s"!', link)
                return
            
            if '#include' in data:
                self.add_work(data['#include'])
                del data['#include']
            
            base_path = os.path.dirname(link[1])
            for mod in data.values():
                if 'logo' in mod:
                    mod['logo'] = util.get(base_path + '/' + mod['logo']).read()
            
            self.post(data)
        elif link[0] == 'fs2mod':
            with tempfile.TemporaryFile() as dl:
                util.download(link[1], dl)
                
                dl.seek(0)
                mod = ModInfo2()
                mod.read_zip(dl)
            
            self.add_work([item[2] for item in mod.dependencies if item[0] == 'fs2mod'])
            self.post(mod.__dict__)
        else:
            logging.error('Fetch type "%s" isn\'t implemented (yet)!', link[0])
    
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
        global shared_files, installed
        skip_files = []
        mod = ModInfo2(settings['mods'][modname])
        
        for path, mods in shared_files.items():
            if path.startswith(mod.folder) and set(mods).issubset(set(installed)):
                # Strip the mod folder away.
                skip_files.append(path[len(mod.folder):].lstrip('/'))
        
        if len(skip_files) > 0:
            logging.info('Will skip the following files: %s', ', '.join(skip_files))
        
        mod.remove(os.path.join(settings['fs2_path'], mod.folder), skip_files)
    
    def finish(self):
        update_list()


class GOGExtractTask(progress.Task):
    def __init__(self, gog_path, dest_path):
        super(GOGExtractTask, self).__init__()
        
        self.done.connect(self.finish)
        self.add_work([(gog_path, dest_path)])
    
    def work(self, paths):
        gog_path, dest_path = paths
        
        progress.start_task(0, 0.03, 'Looking for InnoExtract...')
        data = util.get(settings['innoextract_link']).read().decode('utf8', 'replace')
        progress.finish_task()
        
        try:
            data = json.loads(data)
        except:
            logging.exception('Failed to read JSON data!')
            return
        
        link = None
        path = None
        for plat, info in data.items():
            if sys.platform.startswith(plat):
                link, path = info
                break
        
        if link is None:
            logging.error('Couldn\'t find an innoextract download for "%s"!', sys.platform)
            return
        
        inno = os.path.join(dest_path, os.path.basename(path))
        with tempfile.TemporaryDirectory() as tempdir:
            archive = os.path.join(tempdir, os.path.basename(link))
            
            progress.start_task(0.03, 0.10, 'Downloading InnoExtract...')
            with open(os.path.join(dest_path, archive), 'wb') as dl:
                util.download(link, dl)
            
            progress.finish_task()
            progress.update(0.13, 'Extracting InnoExtract...')
            
            util.extract_archive(archive, tempdir)
            shutil.move(os.path.join(tempdir, path), inno)
        
        # Make it executable
        mode = os.stat(inno).st_mode
        os.chmod(inno, mode | stat.S_IXUSR)

        progress.start_task(0.15, 0.75, 'Extracting FS2: %s')
        try:
            cmd = [inno, '-L', '-s', '-p', '-e', gog_path]
            logging.info('Running %s...', ' '.join(cmd))
            
            opts = dict()
            if sys.platform.startswith('win'):
                si = subprocess.STARTUPINFO()
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                
                opts['startupinfo'] = si
                opts['stdin'] = subprocess.PIPE
            
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=dest_path, **opts)
            
            if sys.platform.startswith('win'):
                p.stdin.close()
            
            buf = ''
            while p.poll() is None:
                while '\r' not in buf:
                    line = p.stdout.read(10)
                    if not line:
                        break
                    buf += line.decode('utf8', 'replace')

                buf = buf.split('\r')
                line = buf.pop(0)
                buf = '\r'.join(buf)
                
                if 'MiB/s' in line:
                    try:
                        if ']' in line:
                            line = line.split(']')[1]
                        
                        line = line.strip().split('MiB/s')[0] + 'MiB/s'
                        percent = float(line.split('%')[0]) / 100

                        progress.update(percent, line)
                    except:
                        logging.exception('Failed to process InnoExtract output!')
                else:
                    if line.strip() == 'not a supported Inno Setup installer':
                        self.post(-1)
                        return
                    
                    logging.info('InnoExtract: %s', line)
        except:
            logging.exception('InnoExtract failed!')
            return
        
        progress.finish_task()
        
        progress.update(0.95, 'Arranging files...')
        self._makedirs(os.path.join(dest_path, 'data/players'))
        self._makedirs(os.path.join(dest_path, 'data/movies'))
        
        for item in glob.glob(os.path.join(dest_path, 'app', '*.vp')):
            shutil.move(item, os.path.join(dest_path, 'data', os.path.basename(item)))
        
        for item in glob.glob(os.path.join(dest_path, 'app/data/players', '*.hcf')):
            shutil.move(item, os.path.join(dest_path, 'data/players', os.path.basename(item)))
        
        for item in glob.glob(os.path.join(dest_path, 'app/data2', '*.mve')):
            shutil.move(item, os.path.join(dest_path, 'data/movies', os.path.basename(item)))
        
        for item in glob.glob(os.path.join(dest_path, 'app/data3', '*.mve')):
            shutil.move(item, os.path.join(dest_path, 'data/movies', os.path.basename(item)))
        
        progress.update(0.99, 'Cleanup...')
        os.unlink(inno)
        shutil.rmtree(os.path.join(dest_path, 'app'), ignore_errors=True)
        shutil.rmtree(os.path.join(dest_path, 'tmp'), ignore_errors=True)
        
        # TODO: Test & improve
        self.post(dest_path)
    
    def _makedirs(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)
    
    def finish(self):
        global settings
        
        results = self.get_results()
        if len(results) < 1:
            QtGui.QMessageBox.critical(main_win, 'Error', 'The Installer failed! Please read the log for more details...')
            return
        elif results[0] == -1:
            QtGui.QMessageBox.critical(main_win, 'Error', 'The selected file wasn\'t a proper Inno Setup installer. Are you shure you selected the right file?')
            return
        else:
            QtGui.QMessageBox.information(main_win, 'Done', 'FS2 was successfully installed.')

        fs2_path = results[0]
        settings['fs2_path'] = fs2_path
        settings['fs2_bin'] = None
        
        for item in glob.glob(os.path.join(fs2_path, 'fs2_*.exe')):
            if os.path.isfile(item):
                settings['fs2_bin'] = os.path.basename(item)
                break
        
        save_settings()
        init_fs2_tab()


# Progress display
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
        
        self.win = init_ui(Ui_Progress(), QtGui.QDialog(main_win))
        self.win.setModal(True)
    
    def show(self):
        progress.reset()
        
        progress.set_callback(self.update_prog)
        progress.update(0, 'Working...')
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
        progress.set_callback(None)
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
            settings['fs2_bin'] = None
    
    if settings['fs2_path'] is None or not os.path.isdir(settings['fs2_path']):
        # Disable mod tab if we don't know where fs2 is.
        main_win.tabs.setTabEnabled(1, False)
        main_win.tabs.setCurrentIndex(0)
        main_win.fs2_bin.hide()
    else:
        fs2_path = settings['fs2_path']
        if settings['fs2_bin'] is not None:
            fs2_path = os.path.join(fs2_path, settings['fs2_bin'])
        
        main_win.tabs.setTabEnabled(1, True)
        main_win.tabs.setCurrentIndex(1)
        main_win.fs2_bin.show()
        main_win.fs2_bin.setText('Selected FS2 Open: ' + os.path.normcase(fs2_path))
        
        update_list()


def do_gog_extract():
    extract_win = init_ui(Ui_Gogextract(), QtGui.QDialog(main_win))

    def select_installer():
        path = QtGui.QFileDialog.getOpenFileName(extract_win, 'Please select the setup_freespace2_*.exe file.',
                                                 os.path.expanduser('~/Downloads'), 'Executable (*.exe)')[0]

        if path is not None:
            if not os.path.isfile(path):
                QtGui.QMessageBox.critical(extract_win, 'Not a file', 'Please select a proper file!')
                return

            extract_win.gogPath.setText(os.path.abspath(path))

    def select_dest():
        path = QtGui.QFileDialog.getExistingDirectory(extract_win, 'Please select the destination directory.', os.path.expanduser('~/Documents'))

        if path is not None:
            if not os.path.isdir(path):
                QtGui.QMessageBox.critical(extract_win, 'Not a directory', 'Please select a proper directory!')
                return

            extract_win.destPath.setText(os.path.abspath(path))

    def validate():
        if os.path.isfile(extract_win.gogPath.text()) and os.path.isdir(extract_win.destPath.text()):
            extract_win.installButton.setEnabled(True)
        else:
            extract_win.installButton.setEnabled(False)

    def do_install():
        # Just to be sure...
        if os.path.isfile(extract_win.gogPath.text()) and os.path.isdir(extract_win.destPath.text()):
            run_task(GOGExtractTask(extract_win.gogPath.text(), extract_win.destPath.text()))
            extract_win.close()

    extract_win.gogPath.textChanged.connect(validate)
    extract_win.destPath.textChanged.connect(validate)

    extract_win.gogButton.clicked.connect(select_installer)
    extract_win.destButton.clicked.connect(select_dest)
    extract_win.cancelButton.clicked.connect(extract_win.close)
    extract_win.installButton.clicked.connect(do_install)

    extract_win.show()


def select_fs2_path(interact=True):
    global settings

    if interact:
        if settings['fs2_path'] is None:
            path = os.path.expanduser('~')
        else:
            path = settings['fs2_path']

        fs2_path = QtGui.QFileDialog.getExistingDirectory(main_win, 'Please select your FS2 directory.', path)
    else:
        fs2_path = settings['fs2_path']

    if fs2_path is not None and os.path.isdir(fs2_path):
        settings['fs2_path'] = os.path.abspath(fs2_path)

        bins = glob.glob(os.path.join(fs2_path, 'fs2_open_*'))
        if len(bins) == 1:
            # Found only one binary, select it by default.

            settings['fs2_bin'] = os.path.basename(bins[0])
        elif len(bins) > 1:
            # Let the user choose.

            select_win = init_ui(Ui_SelectList(), QtGui.QDialog(main_win))
            has_default = False
            bins.sort()

            for i, path in enumerate(bins):
                path = os.path.basename(path)
                select_win.listWidget.addItem(path)

                if not has_default and not (path.endswith('_DEBUG') or path.endswith('-DEBUG.exe')):
                    # Select the first non-debug build as default.

                    select_win.listWidget.setCurrentRow(i)
                    has_default = True

            select_win.listWidget.itemDoubleClicked.connect(select_win.accept)
            select_win.okButton.clicked.connect(select_win.accept)
            select_win.cancelButton.clicked.connect(select_win.reject)

            if select_win.exec_() == QtGui.QDialog.Accepted:
                settings['fs2_bin'] = select_win.listWidget.currentItem().text()
        else:
            settings['fs2_bin'] = None

        save_settings()
        init_fs2_tab()


def run_fs2():
    fs2_bin = os.path.join(settings['fs2_path'], settings['fs2_bin'])
    mode = os.stat(fs2_bin).st_mode
    if mode & stat.S_IXUSR != stat.S_IXUSR:
        # Make it executable.
        os.chmod(fs2_bin, mode | stat.S_IXUSR)

    p = subprocess.Popen([fs2_bin], cwd=settings['fs2_path'])

    time.sleep(0.5)
    if p.poll() is not None:
        QtGui.QMessageBox.critical(main_win, 'Failed', 'Starting FS2 Open (%s) failed! (return code: %d)' % (os.path.join(settings['fs2_path'], settings['fs2_bin']), p.returncode))


# Mod tab
def fetch_list():
    run_task(FetchTask())


def _update_list(results):
    global settings, main_win, installed, shared_files
    
    installed = []
    rows = dict()
    files = dict()
    
    for mod, archives, s, c, m in results:
        for item in mod.contents.keys():
            path = util.pjoin(mod.folder, item)
            
            if path in files:
                files[path].append(mod.name)
            else:
                files[path] = [mod.name]
    
    shared_files = {}
    for path, mods in files.items():
        if len(mods) > 1:
            shared_files[path] = mods
    
    shared_set = set(shared_files.keys())
    
    for mod, archives, s, c, m in results:
        my_shared = shared_set & set([util.pjoin(mod.folder, item) for item in mod.contents.keys()])
        
        if s == c:
            cstate = QtCore.Qt.Checked
            status = 'Installed'
            installed.append(mod.name)
        elif s == 0 or s == len(my_shared):
            cstate = QtCore.Qt.Unchecked
            status = 'Not installed'
            
            if len(my_shared) > 0:
                status += ' (%d shared files)' % len(my_shared)
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
    
    if settings['fs2_path'] is None:
        return
    
    if settings['mods'] is None:
        fetch_list()
    else:
        run_task(CheckTask())


def resolve_deps(mods):
    global installed

    deps = set()
    modlist = settings['mods'].copy()
    
    for name, data in modlist.items():
        modlist[name] = ModInfo2(data)
    
    for name in mods:
        deps |= modlist[name].lookup_deps(modlist, installed)
    
    return list(deps - set(mods))


def autoselect_deps(item, col):
    if col != 0 or item.checkState(0) != QtCore.Qt.Checked:
        return
    
    deps = resolve_deps([item.text(0)])
    items = read_tree(main_win.modTree)
    for row, parent in items:
        if row.text(0) in deps and row.checkState(0) == QtCore.Qt.Unchecked:
            row.setCheckState(0, QtCore.Qt.Checked)


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
            deps = resolve_deps([mod.name])

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
    
    infowin.note.appendPlainText('\n\nContents:\n* ' + '\n* '.join([util.pjoin(mod.folder, item) for item in sorted(mod.contents.keys())]))
    
    infowin.closeButton.clicked.connect(infowin.close)
    infowin.runButton.clicked.connect(do_run)
    infowin.show()


def run_mod(mod):
    if settings['fs2_bin'] is None:
        select_fs2_path(False)

        if settings['fs2_bin'] is None:
            QtGui.QMessageBox.critical(main_win, 'Error', 'I couldn\'t find a FS2 executable. Can\'t run FS2!!')
            return

    modpath = util.ipath(os.path.join(settings['fs2_path'], mod.folder))
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
                elif line[0] in ('secondrylist', 'secondarylist'):
                    seclist = line[1].split(',')
        
        if ini == 'mod.ini':
            ini = os.path.basename(modpath) + '/' + ini

        # Build the whole list for -mod
        modfolder = ','.join(primlist + [ini.split('/')[0]] + seclist).strip(',').replace(',,', ',')
    
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


def read_tree(parent, items=None):
    if items is None:
        items = []
    
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
        install = install + resolve_deps(install)

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
    else:
        my_path = os.path.dirname(__file__)
        if my_path != '':
            os.chdir(my_path)
    
    if not os.path.isdir(settings_path):
        os.makedirs(settings_path)
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')
    if sys.platform.startswith('win'):
        # Windows won't display a console so write our log messages to a file.
        handler = logging.FileHandler(os.path.join(settings_path, 'log.txt'), 'w')
        handler.setFormatter(logging.Formatter('%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s'))
        logging.getLogger().addHandler(handler)
    
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
        fso_parser.HASH_CACHE = settings['hash_cache']
    
    app = QtGui.QApplication([])
    
    if os.path.isfile('hlp.png'):
        app.setWindowIcon(QtGui.QIcon('hlp.png'))

    if not util.test_7z():
        QtGui.QMessageBox.critical(None, 'Error', 'I can\'t find "7z"! Please install it and run this program again.', QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
        return

    main_win = init_ui(Ui_MainWindow(), QtGui.QMainWindow())
    progress_win = ProgressDisplay()

    if hasattr(sys, 'frozen'):
        # Add note about bundled content.
        # NOTE: This will appear even when this script is bundled with py2exe or a similiar program.
        main_win.aboutLabel.setText(main_win.aboutLabel.text().replace('</body>', '<p>' +
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
    
    main_win.modTree.itemActivated.connect(select_mod)
    main_win.modTree.itemChanged.connect(autoselect_deps)
    main_win.modTree.sortItems(0, QtCore.Qt.AscendingOrder)
    main_win.modTree.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
    
    pmaster.start_workers(10)
    QtCore.QTimer.singleShot(300, update_list)

    main_win.show()
    app.exec_()
    
    settings['hash_cache'] = dict()
    for path, info in fso_parser.HASH_CACHE.items():
        # Skip deleted files
        if os.path.exists(path):
            settings['hash_cache'][path] = info
    
    save_settings()

if __name__ == '__main__':
    main()
