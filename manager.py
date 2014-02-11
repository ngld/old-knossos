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

import sys
if __name__ == '__main__':
    # Allow other modules to user "import manager"
    sys.modules['manager'] = sys.modules['__main__']

import os
import logging
import pickle
import subprocess
import stat
import glob
import time
import six
import progress
import util
import fso_parser
from six.moves.urllib import parse as urlparse
from qt import QtCore, QtGui
from ui.main import Ui_MainWindow
from ui.modinfo import Ui_Dialog as Ui_Modinfo
from ui.gogextract import Ui_Dialog as Ui_Gogextract
from ui.select_list import Ui_Dialog as Ui_SelectList
from ui.add_repo import Ui_Dialog as Ui_AddRepo
from fs2mod import ModInfo2
from tasks import *

VERSION = '0.1'
main_win = None
progress_win = None
installed = None
shared_files = {}
pmaster = progress.Master()
settings = {
    'fs2_bin': None,
    'fs2_path': None,
    'mods': None,
    'known_files': {},
    'hash_cache': None,
    'repos': [('json', 'http://dev.tproxy.de/fs2/all.json', 'ngld\'s HLP Mirror')],
    'innoextract_link': 'http://dev.tproxy.de/fs2/innoextract.txt'
}

settings_path = os.path.expanduser('~/.fs2mod-py')
if sys.platform.startswith('win'):
    settings_path = os.path.expandvars('$APPDATA/fs2mod-py')


class _SignalContainer(QtCore.QObject):
    fs2_launched = QtCore.Signal()
    list_updated = QtCore.Signal()

signals = _SignalContainer()


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
    
    signals.fs2_launched.emit()


# Mod tab
def fetch_list():
    return run_task(FetchTask())


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
        if len(settings['mods']) > 0:
            return run_task(CheckTask(settings['mods'].values()), _update_list)


def _get_installed(results):
    global installed
    
    installed = []
    
    for mod, archives, s, c, m in results:
        if s == c:
            installed.append(mod.name)


def get_installed():
    return run_task(CheckTask(settings['mods'].values()), _get_installed)


def resolve_deps(mods, skip_installed=True):
    global installed

    deps = set()
    modlist = settings['mods'].copy()
    
    for name, data in modlist.items():
        modlist[name] = ModInfo2(data)
    
    for name in mods:
        deps |= modlist[name].lookup_deps(modlist)
    
    if skip_installed:
        deps -= set(installed)
    
    return list(deps - set(mods))


def autoselect_deps(item, col):
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
    is_installed = item.data(0, QtCore.Qt.UserRole) == QtCore.Qt.Checked
    check_msgs = item.data(0, QtCore.Qt.UserRole + 1)
    mod = ModInfo2(settings['mods'][name])
    
    def do_run():
        run_mod(mod)
    
    infowin = util.init_ui(Ui_Modinfo(), QtGui.QDialog(main_win))
    infowin.setModal(True)
    
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
    infowin.runButton.clicked.connect(do_run)
    infowin.show()
    
    infowin.note.verticalScrollBar().setValue(0)


def run_mod(mod):
    global installed
    
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
    
    # Correct the case
    modfolder = modfolder.split(',')
    for i, item in enumerate(modfolder):
        modfolder[i] = os.path.basename(util.ipath(os.path.join(settings['fs2_path'], item)))
    
    modfolder = ','.join(modfolder)
    
    # Now look for the user directory...
    if sys.platform in ('linux2', 'linux'):
        # TODO: What about Mac OS ?
        path = os.path.expanduser('~/.fs2_open')
    else:
        path = settings['fs2_path']
    
    cmdline = []
    path = os.path.join(path, 'data/cmdline_fso.cfg')
    if os.path.exists(path):
        try:
            with open(path, 'r') as stream:
                cmdline = stream.read().strip().split(' ')
        except:
            logging.exception('Failed to read "%s", assuming empty cmdline.', path)
    
    mod_found = False
    for i, part in enumerate(cmdline):
        if part.strip() == '-mod':
            mod_found = True
            cmdline[i + 1] = modfolder
            break
    
    if not mod_found:
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
        item = QtGui.QListWidgetItem(repo[2], main_win.sourceList)
        item.setData(QtCore.Qt.UserRole, i)


def _edit_repo(repo=None, idx=None):
    win = util.init_ui(Ui_AddRepo(), QtGui.QDialog(main_win))
    
    def update_type():
        if win.typeJson.isChecked():
            win.sourceButton.hide()
        else:
            win.sourceButton.show()
    
    def source_select():
        path = QtGui.QFileDialog.getOpenFileName(win, 'Please select a source.', '', 'fs2mod File (*.fs2mod)')
        if isinstance(path, tuple):
            path = path[0]
        
        if path is not None and os.path.isfile(path):
            win.source.setText(os.path.abspath(path))
            
            if win.typeFs2mod.isChecked():
                try:
                    mod = ModInfo2()
                    mod.read_zip(path)
                    
                    win.title.setText(mod.name + ' (fs2mod)')
                except:
                    logging.exception('Failed to read "%s". Can\'t determine title.')
    
    win.typeJson.toggled.connect(update_type)
    win.typeFs2mod.toggled.connect(update_type)
    
    win.sourceButton.clicked.connect(source_select)
    
    win.okButton.clicked.connect(win.accept)
    win.cancelButton.clicked.connect(win.reject)
    
    if repo is not None:
        if repo[0] == 'json':
            win.typeJson.setChecked(True)
        else:
            win.typeFs2mod.setChecked(True)
        
        win.source.setText(repo[1])
        win.title.setText(repo[2])
    
    if win.exec_() == QtGui.QMessageBox.Accepted:
        if win.typeJson.isChecked():
            type_ = 'json'
        else:
            type_ = 'fs2mod'
        
        if idx is None:
            settings['repos'].append((type_, win.source.text(), win.title.text()))
        else:
            settings['repos'][idx] = (type_, win.source.text(), win.title.text())
        
        save_settings()
        update_repo_list()
        #fetch_list()


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


def install_scheme_handler():
    tpl = r"""Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\fs2]
"URLProtocol"=""

[HKEY_CLASSES_ROOT\fs2\shell]

[HKEY_CLASSES_ROOT\fs2\shell\open]

[HKEY_CLASSES_ROOT\fs2\shell\open\command]
@="{PATH} \"%1\""
"""
    if hasattr(sys, 'frozen'):
        my_path = os.path.abspath(sys.executable)
    else:
        my_path = os.path.abspath(__file__)
    
    fd, path = tempfile.mkstemp('.reg')
    os.write(fd, tpl.replace('{PATH}', my_path.replace('\\', '\\\\')).replace('\n', '\r\n'))
    os.close(fd)
    
    try:
        subprocess.call(['regedit', path])
    except:
        logging.exception('Failed!')
    
    os.unlink(path)


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
        save_settings()
    
    if settings['hash_cache'] is not None:
        fso_parser.HASH_CACHE = settings['hash_cache']
    
    pmaster.start_workers(10)
    app = QtGui.QApplication([])
    
    if os.path.isfile('hlp.png'):
        app.setWindowIcon(QtGui.QIcon('hlp.png'))

    if not util.test_7z():
        QtGui.QMessageBox.critical(None, 'Error', 'I can\'t find "7z"! Please install it and run this program again.', QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
        return

    return app


def main():
    global VERSION, main_win, progress_win
    
    app = init()
    main_win = util.init_ui(Ui_MainWindow(), QtGui.QMainWindow())
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
    
    if sys.platform.startswith('win'):
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
    
    QtCore.QTimer.singleShot(1, init_fs2_tab)

    main_win.show()
    app.exec_()
    
    settings['hash_cache'] = dict()
    for path, info in fso_parser.HASH_CACHE.items():
        # Skip deleted files
        if os.path.exists(path):
            settings['hash_cache'][path] = info
    
    save_settings()


def scheme_handler(o_link, app=None):
    global progress_win
    
    def recall():
        scheme_handler(o_link, app)
    
    if app is None:
        app = init()
        progress_win = progress.ProgressDisplay()
        
        # Force an update of the mod list.
        settings['mods'] = None
        
        QtCore.QTimer.singleShot(1, recall)
        app.exec_()
        return
    
    if not o_link.startswith(('fs2://', 'fso://')):
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'I don\'t know how to handle "%s"! I only know fs2:// .' % (o_link))
        app.quit()
        return
    
    link = urlparse.unquote(o_link).split('/')
    action = link[2]
    params = link[3:]
    
    if len(params) == 0:
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Not enough arguments!')
        app.quit()
        return
    
    if action in ('run', 'install'):
        if settings['mods'] is None or len(settings['mods']) == 0:
            task = fetch_list()
            task.done.connect(recall)
            return
        
        if installed is None:
            task = get_installed()
            task.done.connect(recall)
            return
        
        # Look for the given mod.
        if params[0] not in settings['mods']:
            QtGui.QMessageBox.critical(None, 'fs2mod-py', 'MOD "%s" wasn\'t found!' % (params[0]))
            app.quit()
            return
        
        mod = ModInfo2(settings['mods'][params[0]])
    
    if action == 'run':
        signals.fs2_launched.connect(app.quit)
        run_mod(mod)
    elif action == 'install':
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
            QtGui.QMessageBox.infomation(None, 'fs2mod-py', 'MOD "%s" is already installed!' % (mod.name))
            app.quit()
    else:
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'The action "%s" is unknown!' % (action))
        app.quit()


if __name__ == '__main__':
    if len(sys.argv) > 1 and '://' in sys.argv[1]:
        scheme_handler(sys.argv[1])
    else:
        main()
