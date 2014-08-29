#!/usr/bin/python
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

from __future__ import absolute_import, print_function
import sys
import logging
if __name__ == '__main__':
    # Allow other modules to use "import manager"
    sys.modules['manager'] = sys.modules['__main__']

# Do the logging config here because gi.repository will use it already on import.
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')

import os
import pickle
import subprocess
import threading
import stat
import glob
import time
import six
from six.moves.urllib import parse as urlparse

from lib import progress, util
from lib.qt import QtCore, QtGui
from ui.main import Ui_MainWindow
from ui.modinfo import Ui_Dialog as Ui_Modinfo
from ui.gogextract import Ui_Dialog as Ui_Gogextract
from ui.select_list import Ui_Dialog as Ui_SelectList
from ui.add_repo import Ui_Dialog as Ui_AddRepo
from ui.splash import Ui_MainWindow as Ui_Splash
from lib.fs2mod import ModInfo2
from lib.tasks import *
from lib.windows import SettingsWindow, SettingsTab, FlagsWindow


try:
    from gi.repository import Unity, Dbusmenu
except ImportError:
    # Can't find Unity.
    Unity = None

VERSION = '0.3-packager'
main_win = None
progress_win = None
splash = None
unity_launcher = None
shared_files = {}
fs2_watcher = None
pmaster = progress.Master()
settings = {
    'fs2_bin': None,
    'fs2_path': None,
    'mods': None,
    'installed_mods': None,
    'cmdlines': {},
    'hash_cache': None,
    'enforce_deps': True,
    'repos': [('http://dev.tproxy.de/fs2/all.json', 'ngld\'s Repo')],
    'innoextract_link': 'http://dev.tproxy.de/fs2/innoextract.txt'
}

settings_path = os.path.expanduser('~/.fs2mod-py')
if sys.platform.startswith('win'):
    settings_path = os.path.expandvars('$APPDATA/fs2mod-py')


class _SignalContainer(QtCore.QObject):
    fs2_launched = QtCore.Signal()
    fs2_failed = QtCore.Signal(int)
    fs2_quit = QtCore.Signal()
    list_updated = QtCore.Signal()

signals = _SignalContainer()


class MainWindow(QtGui.QMainWindow):

    def changeEvent(self, event):
        global unity_launcher
        if event.type() == QtCore.QEvent.ActivationChange:
            if main_win.isActiveWindow():
                if Unity:
                    if unity_launcher.get_property("urgent"):
                        unity_launcher.set_property("urgent", False)
    
        return super(MainWindow, self).changeEvent(event)


class Fs2Watcher(threading.Thread):
    _params = None
    
    def __init__(self, params=None):
        super(Fs2Watcher, self).__init__()
        
        if params is None:
            self._params = []
        else:
            self._params = params
        
        self.daemon = True
        self.start()
    
    def run(self):
        global settings, fs2_watcher
        
        fs2_bin = os.path.join(settings['fs2_path'], settings['fs2_bin'])
        mode = os.stat(fs2_bin).st_mode
        if mode & stat.S_IXUSR != stat.S_IXUSR:
            # Make it executable.
            os.chmod(fs2_bin, mode | stat.S_IXUSR)
        
        p = subprocess.Popen([fs2_bin] + self._params, cwd=settings['fs2_path'])

        time.sleep(0.3)
        if p.poll() is not None:
            signals.fs2_failed.emit(p.returncode)
            self.failed_msg(p)
            return
        
        signals.fs2_launched.emit()
        p.wait()
        signals.fs2_quit.emit()
    
    @util.run_in_qt
    def failed_msg(self, p):
        global main_win, settings
        
        msg = 'Starting FS2 Open (%s) failed! (return code: %d)' % (os.path.join(settings['fs2_path'], settings['fs2_bin']), p.returncode)
        QtGui.QMessageBox.critical(main_win, 'Failed', msg)

    
def run_task(task, cb=None):
    def wrapper():
        cb(task.get_results())
    
    if cb is not None:
        task.done.connect(wrapper)
    
    progress_win.add_task(task)
    pmaster.add_task(task)
    return task


# FS2 tab
def save_settings():
    settings['hash_cache'] = dict()
    for path, info in util.HASH_CACHE.items():
        # Skip deleted files
        if os.path.exists(path):
            settings['hash_cache'][path] = info
    
    for mod in settings['cmdlines'].copy():
        if mod not in installed and mod != '#default':
            del settings['cmdlines'][mod]
    
    with open(os.path.join(settings_path, 'settings.pick'), 'wb') as stream:
        pickle.dump(settings, stream, 2)


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
        main_win.fs2Settings.setDisabled(True)
    else:
        fs2_path = settings['fs2_path']
        if settings['fs2_bin'] is not None:
            fs2_path = os.path.join(fs2_path, settings['fs2_bin'])
        
        main_win.tabs.setTabEnabled(1, True)
        main_win.tabs.setCurrentIndex(1)
        main_win.fs2_bin.show()
        main_win.fs2_bin.setText('Selected FS2 Open: ' + os.path.normcase(fs2_path))
        main_win.fs2Settings.setDisabled(False)
        
        update_list()


def show_tab(a, b, tab):
    global main_win
    main_win.tabs.setCurrentIndex(tab)
    main_win.activateWindow()

    
def go_to_hlp(a, b, tab):
    QtGui.QDesktopServices.openUrl("http://www.hard-light.net/")


def do_gog_extract():
    extract_win = util.init_ui(Ui_Gogextract(), QtGui.QDialog(main_win))

    def select_installer():
        path = QtGui.QFileDialog.getOpenFileName(extract_win, 'Please select the setup_freespace2_*.exe file.',
                                                 os.path.expanduser('~/Downloads'), 'Executable (*.exe)')
        if isinstance(path, tuple):
            path = path[0]
        
        if path is not None and path != '':
            if not os.path.isfile(path):
                QtGui.QMessageBox.critical(extract_win, 'Not a file', 'Please select a proper file!')
                return

            extract_win.gogPath.setText(os.path.abspath(path))

    def select_dest():
        path = QtGui.QFileDialog.getExistingDirectory(extract_win, 'Please select the destination directory.', os.path.expanduser('~/Documents'))

        if path is not None and path != '':
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

            select_win = util.init_ui(Ui_SelectList(), QtGui.QDialog(main_win))
            has_default = False
            bins.sort()

            for i, path in enumerate(bins):
                path = os.path.basename(path)
                select_win.listWidget.addItem(path)

                if not has_default and not (path.endswith('_DEBUG') and '-DEBUG' not in path):
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


def select_fs2_path_handler():
    select_fs2_path()


def run_fs2(params=None):
    global fs2_watcher
    
    if fs2_watcher is None or not fs2_watcher.is_alive():
        fs2_watcher = Fs2Watcher(params)
        return True
    else:
        return False


# Mod tab
def fetch_list():
    return run_task(FetchTask())


def build_mod_tree(mod=None, parent_el=None):
    if mod is None:
        mods = settings['mods'].get_tree()
    else:
        mods = mod.get_submods()

    rows = dict()

    for mod in mods:
        row = QtGui.QTreeWidgetItem((mod.name, mod.version, ''))
        rows[mod.id] = (row, dict())

        if parent_el is None:
            main_win.modTree.addTopLevelItem(row)
        else:
            parent_el.addChild(row)

        rows.update(build_mod_tree(mod, row))

    return rows


def _update_list(results):
    global settings, main_win, shared_files
    
    # Make sure the mod tree is empty.
    main_win.modTree.clear()

    installed = []
    rows = build_mod_tree()
    files = dict()
    
    for pkg, archives, s, c, m in results:
        for item in mod.get_files().keys():
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
    
    for pkg, archives, s, c, m in results:
        my_shared = shared_set & set([util.pjoin(mod.folder, item) for item in pkg.get_files().keys()])
        
        if s == c:
            cstate = QtCore.Qt.Checked
            status = 'Installed'
            installed.append(pkg)
        elif s == 0 or s == len(my_shared):
            cstate = QtCore.Qt.Unchecked
            status = 'Not installed'
            
            if len(my_shared) > 0:
                status += ' (%d shared files)' % len(my_shared)
        else:
            cstate = QtCore.Qt.PartiallyChecked
            status = '%d corrupted or updated files' % (c - s)
        
        row = QtGui.QTreeWidgetItem((pkg.name, mod.version, status))
        row.setCheckState(0, cstate)
        row.setData(0, QtCore.Qt.UserRole, cstate)
        row.setData(0, QtCore.Qt.UserRole + 1, m)
        #row.setData(0, QtCore.Qt.UserRole + 2, pkg)
        
        mid = pkg.get_mod().id
        rows[mid][1][pkg.name] = (row, pkg)
        rows[mid][0].addChild(row)
    
    for mod in settings['mods'].get_list():
        rc = 0
        ri = 0
        for pkg in mod.packages:
            if pkg.status == 'required':
                if pkg in installed:
                    ri += 1
                
                rc += 1

        if ri == 0:
            state = QtCore.Qt.Unchecked
        elif ri == rc:
            state = QtCore.Qt.Checked
        else:
            state = QtCore.Qt.PartiallyChecked

        rows[mod.id][0].setCheckState(0, state)

    if not main_win.isActiveWindow():
        if Unity:
            if not unity_launcher.get_property("urgent"):
                unity_launcher.set_property("urgent", True)


def update_list():
    global settings, main_win
    
    main_win.modTree.clear()
    
    if settings['fs2_path'] is None:
        return
    
    if settings['mods'] is None:
        fetch_list()
    else:
        return run_task(CheckTask(settings['mods'].get_list()), _update_list)


def _get_installed(results):
    global installed
    
    installed = []
    
    for mod, archives, s, c, m in results:
        if s == c:
            installed.append(mod.name)


def get_installed():
    return run_task(CheckTask(settings['mods'].values()), _get_installed)


def autoselect_deps(item, col):
    global settings, installed
    
    if settings['enforce_deps']:
        checked = set()
        items = read_tree(main_win.modTree)
        for row, p in items:
            if row.checkState(0) == QtCore.Qt.Checked:
                checked.add(row.text(0))
        
        deps = resolve_deps(checked, False)
        for row, p in items:
            if row.text(0) in deps:
                row.setCheckState(0, QtCore.Qt.Checked)
    else:
        if col != 0 or item.checkState(0) != QtCore.Qt.Checked:
            return
        
        deps = resolve_deps([item.text(0)])
        items = read_tree(main_win.modTree)
        for row, parent in items:
            if row.text(0) in deps and row.checkState(0) == QtCore.Qt.Unchecked:
                row.setCheckState(0, QtCore.Qt.Checked)


def reset_selection():
    items = read_tree(main_win.modTree)
    for row, parent in items:
        row.setCheckState(0, QtCore.Qt.CheckState(row.data(0, QtCore.Qt.UserRole)))


def select_mod(item, col):
    global installed
    
    name = item.text(0)
    check_msgs = item.data(0, QtCore.Qt.UserRole + 1)
    mod = ModInfo2(settings['mods'][name])
    infowin = util.init_ui(Ui_Modinfo(), QtGui.QDialog(main_win))
    infowin.setModal(True)
    
    def do_run():
        run_mod(mod)
    
    def show_settings():
        FlagsWindow(infowin, mod)
    
    if mod.version not in (None, ''):
        infowin.modname.setText(mod.name + ' - ' + mod.version)
    else:
        infowin.modname.setText(mod.name)
    
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
    
    deps = resolve_deps([mod.name], False)
    if len(deps) > 0:
        lines = []
        for dep in deps:
            line = '* ' + dep
            if dep in installed:
                line += ' (installed)'
            
            lines.append(line)
        
        infowin.note.appendPlainText('\nDependencies:\n' + '\n'.join(lines))
    
    infowin.note.appendPlainText('\nContents:\n* ' + '\n* '.join([util.pjoin(mod.folder, item) for item in sorted(mod.contents.keys())]))
    
    infowin.closeButton.clicked.connect(infowin.close)
    infowin.settingsButton.clicked.connect(show_settings)
    infowin.runButton.clicked.connect(do_run)
    infowin.show()
    
    infowin.note.verticalScrollBar().setValue(0)


def run_mod(mod):
    global installed
    
    if mod is None:
        mod = ModInfo2()
    
    modpath = util.ipath(os.path.join(settings['fs2_path'], mod.folder))
    ini = None
    modfolder = None
    
    def check_install():
        # TODO: Is there a better way to check if the installation failed?
        if not os.path.isdir(modpath):
            QtGui.QMessageBox.critical(main_win, 'Error', 'Failed to install "%s"! Read the log for more information.' % (mod.name))
        else:
            installed.append(mod.name)
            run_mod(mod)
    
    if settings['fs2_bin'] is None:
        select_fs2_path(False)

        if settings['fs2_bin'] is None:
            QtGui.QMessageBox.critical(main_win, 'Error', 'I couldn\'t find a FS2 executable. Can\'t run FS2!!')
            return
    
    if mod.name not in installed and mod.name != '':
        deps = resolve_deps([mod.name])

        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Question)
        msg.setText('You don\'t have %s, yet. Shall I install it?' % (mod.name))
        msg.setInformativeText('%s will be installed.' % (', '.join([mod.name] + deps)))
        msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        msg.setDefaultButton(QtGui.QMessageBox.Yes)
        
        if msg.exec_() == QtGui.QMessageBox.Yes:
            task = InstallTask([mod.name] + deps)
            task.done.connect(check_install)
            run_task(task)
        
        return
    
    # Look for the mod.ini
    for item in mod.contents:
        if os.path.basename(item).lower() == 'mod.ini':
            ini = item
            break
    
    if ini is not None and os.path.isfile(os.path.join(modpath, ini)):
        # mod.ini was found, now read its "[multimod]" section.
        primlist = []
        seclist = []
        
        try:
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
        except:
            logging.exception('Failed to read %s!', os.path.join(modpath, ini))
        
        if ini == 'mod.ini':
            ini = os.path.basename(modpath) + '/' + ini

        # Build the whole list for -mod
        modfolder = ','.join(primlist + [ini.split('/')[0]] + seclist).strip(',').replace(',,', ',')
    else:
        # No mod.ini found, look for the first subdirectory then.
        if mod.folder == '':
            for item in mod.contents:
                if item.lower().endswith('.vp'):
                    modfolder = item.split('/')[0]
                    break
        else:
            modfolder = mod.folder.split('/')[0]
    
    if modfolder is not None:
        # Correct the case
        modfolder = modfolder.split(',')
        for i, item in enumerate(modfolder):
            modfolder[i] = os.path.basename(util.ipath(os.path.join(settings['fs2_path'], item)))
        
        modfolder = ','.join(modfolder)
    mod_found = False
    
    # Look for the cmdline path.
    if sys.platform.startswith('linux'):
        # TODO: What about Mac OS ?
        path = os.path.expanduser('~/.fs2_open')
    else:
        path = settings['fs2_path']
    
    path = os.path.join(path, 'data/cmdline_fso.cfg')
    
    if mod.name in settings['cmdlines']:
        # We have a saved cmdline for this mod.
        cmdline = settings['cmdlines'][mod.name][:]
    elif '#default' in settings['cmdlines']:
        # We have a default cmdline.
        cmdline = settings['cmdlines']['#default'][:]
    else:
        # Read the current cmdline.
        cmdline = []
        if os.path.exists(path):
            try:
                with open(path, 'r') as stream:
                    cmdline = stream.read().strip().split(' ')
            except:
                logging.exception('Failed to read "%s", assuming empty cmdline.', path)
        
        if modfolder is not None:
            for i, part in enumerate(cmdline):
                if part.strip() == '-mod':
                    mod_found = True
                    cmdline[i + 1] = modfolder
                    break
    
    if modfolder is not None and not mod_found:
        cmdline.append('-mod')
        cmdline.append(modfolder)
    
    try:
        with open(path, 'w') as stream:
            stream.write(' '.join(cmdline))
    except:
        logging.exception('Failed to modify "%s". Not starting FS2!!', path)
        
        QtGui.QMessageBox.critical(main_win, 'Error', 'Failed to edit "%s"! I can\'t change the current MOD!' % path)
    else:
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
        # NOTE: Dependencies are auto-selected now. Don't force them on the user.
        # install = install + resolve_deps(install)

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


# Settings tab
def update_repo_list():
    main_win.sourceList.clear()
    
    for i, repo in enumerate(settings['repos']):
        item = QtGui.QListWidgetItem(repo[1], main_win.sourceList)
        item.setData(QtCore.Qt.UserRole, i)


def _edit_repo(repo=None, idx=None):
    win = util.init_ui(Ui_AddRepo(), QtGui.QDialog(main_win))
    
    win.okButton.clicked.connect(win.accept)
    win.cancelButton.clicked.connect(win.reject)
    
    if repo is not None:
        win.source.setText(repo[0])
        win.title.setText(repo[1])
    
    if win.exec_() == QtGui.QMessageBox.Accepted:
        source = win.source.text()
        title = win.title.text()
        
        if idx is None:
            found = False
            
            for r_source, r_title in settings['repos']:
                if r_source == source:
                    found = True
                    QtGui.QMessageBox.critical(main_win, 'Error', 'This source is already in the list! (As "%s")' % (r_title))
                    break
            
            if not found:
                settings['repos'].append((source, title))
        else:
            settings['repos'][idx] = (source, title)
        
        save_settings()
        update_repo_list()


def ql_add_repo(a, b, tab):
    main_win.tabs.setCurrentIndex(tab)
    main_win.activateWindow()
    add_repo()


def add_repo():
    _edit_repo()


def edit_repo():
    item = main_win.sourceList.currentItem()
    if item is not None:
        idx = item.data(QtCore.Qt.UserRole)
        _edit_repo(settings['repos'][idx], idx)


def remove_repo():
    item = main_win.sourceList.currentItem()
    if item is not None:
        idx = item.data(QtCore.Qt.UserRole)
        answer = QtGui.QMessageBox.question(main_win, 'Are you sure?', 'Do you really want to remove "%s"?' % (item.text()),
                                            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        
        if answer == QtGui.QMessageBox.Yes:
            del settings['repos'][idx]
            
            save_settings()
            update_repo_list()


def reorder_repos(parent, s_start, s_end, d_parent, d_row):
    global settings
    
    repos = []
    for row in range(0, main_win.sourceList.count()):
        item = main_win.sourceList.item(row)
        repos.append(settings['repos'][item.data(QtCore.Qt.UserRole)])
    
    settings['repos'] = repos
    save_settings()
    
    # NOTE: This call is normally redundant but I want to make sure that
    # the displayed list is always the same as the actual list in settings['repos'].
    # Once this feature is stable this call can be removed.
    update_repo_list()


def install_scheme_handler():
    if hasattr(sys, 'frozen'):
        my_path = os.path.abspath(sys.executable)
    else:
        my_path = os.path.abspath(__file__)
            
    if sys.platform.startswith('win'):
        tpl = r"""Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\fs2]
"URLProtocol"=""

[HKEY_CLASSES_ROOT\fs2\shell]

[HKEY_CLASSES_ROOT\fs2\shell\open]

[HKEY_CLASSES_ROOT\fs2\shell\open\command]
@="{PATH} \"%1\""
"""
        
        fd, path = tempfile.mkstemp('.reg')
        os.write(fd, tpl.replace('{PATH}', my_path.replace('\\', '\\\\')).replace('\n', '\r\n'))
        os.close(fd)
        
        try:
            subprocess.call(['regedit', path])
        except:
            logging.exception('Failed!')
        
        os.unlink(path)
        
    elif sys.platform.startswith('linux'):
        tpl_desktop = r"""[Desktop Entry]
Name=fs2mod-py
Exec={PYTHON} {PATH} %U
Icon={ICON_PATH}
Type=Application
Terminal=false
MimeType=x-scheme-handler/fso;
"""

        tpl_mime_type = 'x-scheme-handler/fso=fs2mod-py.desktop;'

        applications_path = os.path.expanduser('~/.local/share/applications/')
        desktop_file = applications_path + 'fs2mod-py.desktop'
        mime_types_file = applications_path + 'mimeapps.list'
        
        tpl_desktop = tpl_desktop.replace('{PYTHON}', os.path.abspath(sys.executable))
        tpl_desktop = tpl_desktop.replace('{PATH}', my_path)
        tpl_desktop = tpl_desktop.replace('{ICON_PATH}', os.path.abspath(os.path.join(os.path.dirname(__file__), 'hlp.png')))
        
        with open(desktop_file, 'w') as output_file:
            output_file.write(tpl_desktop)
        
        found = False
        with open(mime_types_file, 'r') as lines:
            for line in lines:
                if tpl_mime_type in line:
                    found = True
                    break
        
        if not found:
            with open(mime_types_file, 'a') as output_file:
                output_file.write(tpl_mime_type)


def update_enforce_deps():
    global settings
    
    settings['enforce_deps'] = main_win.enforceDeps.checkState() == QtCore.Qt.Checked
    save_settings()


def show_fs2settings():
    SettingsWindow(None)


def init():
    global settings
    
    if hasattr(sys, 'frozen'):
        if hasattr(sys, '_MEIPASS'):
            os.chdir(sys._MEIPASS)
        else:
            os.chdir(os.path.dirname(sys.executable))
        
        if sys.platform.startswith('win') and os.path.isfile('7z.exe'):
            util.SEVEN_PATH = os.path.abspath('7z.exe')
    else:
        if sys.platform.startswith('win') and os.path.isfile('7z.exe'):
            util.SEVEN_PATH = os.path.abspath('7z.exe')
        
        my_path = os.path.dirname(__file__)
        if my_path != '':
            os.chdir(my_path)
    
    if not os.path.isdir(settings_path):
        os.makedirs(settings_path)
    
    if sys.platform.startswith('win'):
        # Windows won't display a console so write our log messages to a file.
        handler = logging.FileHandler(os.path.join(settings_path, 'log.txt'), 'w')
        handler.setFormatter(logging.Formatter('%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s'))
        logging.getLogger().addHandler(handler)
    
    # Try to load our settings.
    spath = os.path.join(settings_path, 'settings.pick')
    if os.path.exists(spath):
        defaults = settings.copy()
        
        try:
            with open(spath, 'rb') as stream:
                if six.PY3:
                    settings.update(pickle.load(stream, encoding='utf8', errors='replace'))
                else:
                    settings.update(pickle.load(stream))
        except:
            logging.exception('Failed to load settings from "%s"!', spath)
        
        # Migration
        if isinstance(settings['repos'], tuple):
            settings['repos'] = defaults['repos']
        
        del defaults
    
    if settings['hash_cache'] is not None:
        util.HASH_CACHE = settings['hash_cache']
    
    pmaster.start_workers(10)
    app = QtGui.QApplication([])
    
    if os.path.isfile('hlp.png'):
        app.setWindowIcon(QtGui.QIcon('hlp.png'))

    if not util.test_7z():
        QtGui.QMessageBox.critical(None, 'Error', 'I can\'t find "7z"! Please install it and run this program again.', QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
        return

    return app


def main():
    global VERSION, main_win, progress_win, unity_launcher
    
    app = init()
    main_win = util.init_ui(Ui_MainWindow(), MainWindow())
    progress_win = progress.ProgressDisplay()

    if hasattr(sys, 'frozen'):
        # Add note about bundled content.
        # NOTE: This will appear even when this script is bundled with py2exe or a similiar program.
        main_win.aboutLabel.setText(main_win.aboutLabel.text().replace('</body>', '<p>' +
                                    'This bundle was created with <a href="http://pyinstaller.org">PyInstaller</a>' +
                                    ' and contains a 7z executable.</p></body>'))
        
        if os.path.isfile('commit'):
            with open('commit', 'r') as data:
                VERSION += '-' + data.read().strip()
    
    if sys.platform.startswith('win') or sys.platform.startswith('linux'):
        main_win.schemeHandler.clicked.connect(install_scheme_handler)
    else:
        main_win.schemeHandler.hide()
    
    tab = main_win.tabs.addTab(QtGui.QWidget(), 'Version: ' + VERSION)
    main_win.tabs.setTabEnabled(tab, False)
    
    signals.list_updated.connect(update_list)
    update_repo_list()
    
    main_win.aboutLabel.linkActivated.connect(QtGui.QDesktopServices.openUrl)
    
    main_win.gogextract.clicked.connect(do_gog_extract)
    main_win.select.clicked.connect(select_fs2_path_handler)

    main_win.apply_sel.clicked.connect(apply_selection)
    main_win.reset_sel.clicked.connect(reset_selection)
    main_win.update.clicked.connect(fetch_list)
    
    main_win.modTree.itemActivated.connect(select_mod)
    main_win.modTree.itemChanged.connect(autoselect_deps)
    main_win.modTree.sortItems(0, QtCore.Qt.AscendingOrder)
    main_win.modTree.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
    
    main_win.addSource.clicked.connect(add_repo)
    main_win.editSource.clicked.connect(edit_repo)
    main_win.removeSource.clicked.connect(remove_repo)
    main_win.sourceList.itemDoubleClicked.connect(edit_repo)
    
    main_win.enforceDeps.setCheckState(QtCore.Qt.Checked if settings['enforce_deps'] else QtCore.Qt.Unchecked)
    main_win.enforceDeps.stateChanged.connect(update_enforce_deps)
    main_win.fs2Settings.clicked.connect(show_fs2settings)
    
    # NOTE: Assign the model to a variable to prevent a segfault with PySide. (WTF?!)
    m = main_win.sourceList.model()
    m.rowsMoved.connect(reorder_repos)
    del m

    SettingsTab(main_win.fsoSettings)
    
    QtCore.QTimer.singleShot(1, init_fs2_tab)
    
    if Unity:
        unity_launcher = Unity.LauncherEntry.get_for_desktop_id('fs2mod-py.desktop')
        
        # We also want a quicklist
        ql = Dbusmenu.Menuitem.new()
        item_fs2 = Dbusmenu.Menuitem.new()
        item_fs2.property_set(Dbusmenu.MENUITEM_PROP_LABEL, 'FS2')
        item_fs2.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        item_mods = Dbusmenu.Menuitem.new()
        item_mods.property_set(Dbusmenu.MENUITEM_PROP_LABEL, 'Mods')
        item_mods.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        item_settings = Dbusmenu.Menuitem.new()
        item_settings.property_set(Dbusmenu.MENUITEM_PROP_LABEL, 'Settings')
        item_settings.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        item_add_repo = Dbusmenu.Menuitem.new()
        item_add_repo.property_set(Dbusmenu.MENUITEM_PROP_LABEL, 'Add Source')
        item_add_repo.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        item_hlp = Dbusmenu.Menuitem.new()
        item_hlp.property_set(Dbusmenu.MENUITEM_PROP_LABEL, 'Browse mods online')
        item_hlp.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, True)
        
        item_fs2.connect(Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED, show_tab, 0)
        item_mods.connect(Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED, show_tab, 1)
        item_settings.connect(Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED, show_tab, 2)
        item_add_repo.connect(Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED, ql_add_repo, 2)
        item_hlp.connect(Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED, go_to_hlp, 2)
        
        ql.child_append(item_fs2)
        ql.child_append(item_mods)
        ql.child_append(item_settings)
        ql.child_append(item_add_repo)
        ql.child_append(item_hlp)
        
        unity_launcher.set_property('quicklist', ql)
    
    main_win.show()
    app.exec_()
    
    save_settings()


scheme_state = {}


def scheme_handler(o_link, app=None):
    global settings, progress_win, splash, scheme_state
    
    def recall():
        scheme_handler(o_link, app)
    
    if app is None:
        app = init()
        progress_win = progress.ProgressDisplay()
        splash = util.init_ui(Ui_Splash(), QtGui.QMainWindow())
        
        # Center the splash window on the screen.
        screen = app.desktop().screenGeometry()
        splash.move((screen.width() - splash.width()) / 2, (screen.height() - splash.height()) / 2)
        splash.show()
        
        # Save all important variables in scheme_state so they will be kept between calls.
        link = urlparse.unquote(o_link).split('/')
        scheme_state['action'] = link[2]
        scheme_state['params'] = link[3:]
        scheme_state['list_fetched'] = False
        
        QtCore.QTimer.singleShot(1, recall)
        app.exec_()
        splash.hide()
        
        save_settings()
        return
    
    if not o_link.startswith(('fs2://', 'fso://')):
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'I don\'t know how to handle "%s"! I only know fs2:// .' % (o_link))
        app.quit()
        return
    
    if len(scheme_state['params']) == 0:
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Not enough arguments!')
        app.quit()
        return
    
    if scheme_state['action'] in ('run', 'install', 'settings'):
        if settings['mods'] is None or len(settings['mods']) == 0:
            splash.label.setText('Fetching mod list...')
            scheme_state['list_fetched'] = True
            task = fetch_list()
            task.done.connect(recall)
            return
        
        if installed is None:
            task = get_installed()
            task.done.connect(recall)
            return
        
        # Look for the given mod.
        if scheme_state['params'][0] not in settings['mods']:
            if scheme_state['list_fetched']:
                QtGui.QMessageBox.critical(None, 'fs2mod-py', 'MOD "%s" wasn\'t found!' % (scheme_state['params'][0]))
                app.quit()
            else:
                settings['mods'] = None
                recall()
                
            return
        
        mod = ModInfo2(settings['mods'][scheme_state['params'][0]])
        
    if scheme_state['action'] == 'run':
        splash.label.setText('Launching FS2...')
        signals.fs2_launched.connect(app.quit)
        signals.fs2_failed.connect(app.quit)
        app.processEvents()
        
        run_mod(mod)
    elif scheme_state['action'] == 'install':
        splash.label.setText('Installing %s...' % (mod.name))
        if mod.name not in installed:
            deps = resolve_deps([mod.name])

            msg = QtGui.QMessageBox()
            msg.setIcon(QtGui.QMessageBox.Question)
            msg.setText('You don\'t have %s, yet. Shall I install it?' % (mod.name))
            msg.setInformativeText('%s will be installed.' % (', '.join([mod.name] + deps)))
            msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            msg.setDefaultButton(QtGui.QMessageBox.Yes)
            
            if msg.exec_() == QtGui.QMessageBox.Yes:
                task = InstallTask([mod.name] + deps)
                task.done.connect(app.quit)
                run_task(task)
        else:
            QtGui.QMessageBox.information(splash, 'fs2mod-py', 'MOD "%s" is already installed!' % (mod.name))
            app.quit()
    elif scheme_state['action'] == 'settings':
        if mod.name not in installed:
            QtGui.QMessageBox.information(splash, 'fs2mod-py', 'MOD "%s" is not yet installed!' % (mod.name))
            app.quit()
        else:
            SettingsWindow(mod, app)
    else:
        QtGui.QMessageBox.critical(splash, 'fs2mod-py', 'The action "%s" is unknown!' % (scheme_state['action']))
        app.quit()


if __name__ == '__main__':
    if len(sys.argv) > 1 and '://' in sys.argv[1]:
        scheme_handler(sys.argv[1])
    else:
        main()
