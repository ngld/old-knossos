#!/usr/bin/python
## Copyright 2014 fs2mod-py authors, see NOTICE file
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
import os
import pickle
import glob
import subprocess
import threading
import stat
import time
import six

from lib import progress, util, repo, api
from lib.qt import QtCore, QtGui
from lib.tasks import FetchTask, InstallTask, CheckUpdateTask
from lib.windows import MainWindow, NebulaWindow, SettingsWindow
from ui.select_list import Ui_Dialog as Ui_SelectList


try:
    from gi.repository import Unity, Dbusmenu
except ImportError:
    # Can't find Unity.
    Unity = None

# The version should follow the http://semver.org guidelines.
# Only remove the -dev tag if you're making a release!
VERSION = '0.0.6-dev'

app = None
main_win = None
unity_launcher = None
shared_files = {}
fs2_watcher = None
pmaster = progress.Master()
installed = None
fso_flags = None

settings = {
    'fs2_bin': None,
    'fs2_path': None,
    'mods': None,
    'installed_mods': {},
    'cmdlines': {},
    'hash_cache': None,
    'enforce_deps': True,
    'max_downloads': 3,
    'repos': [],
    'innoextract_link': 'http://dev.tproxy.de/fs2/innoextract.txt',
    'nebula_link': 'http://neubla.tproxy.de/',
    'update_link': 'https://dev.tproxy.de/knossos',
    'ui_mode': 'nebula'
}

settings_path = os.path.expanduser('~/.fs2mod-py')
if sys.platform.startswith('win'):
    settings_path = os.path.expandvars('$APPDATA/fs2mod-py')


class _SignalContainer(QtCore.QObject):
    fs2_launched = QtCore.Signal()
    fs2_failed = QtCore.Signal(int)
    fs2_quit = QtCore.Signal()
    list_updated = QtCore.Signal()
    repo_updated = QtCore.Signal()
    update_avail = QtCore.Signal('QVariant')

signals = _SignalContainer()


class QMainWindow(QtGui.QMainWindow):
    closed = QtCore.Signal()
    
    def closeEvent(self, e):
        self.closed.emit()
        e.accept()

    def changeEvent(self, event):
        global unity_launcher
        if event.type() == QtCore.QEvent.ActivationChange:
            if Unity and self.isActiveWindow() and unity_launcher.get_property('urgent'):
                unity_launcher.set_property('urgent', False)
    
        return super(QMainWindow, self).changeEvent(event)


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
        QtGui.QMessageBox.critical(app.activeWindow(), 'Failed', msg)

    
def run_task(task, cb=None):
    def wrapper():
        cb(task.get_results())
    
    if cb is not None:
        task.done.connect(wrapper)
    
    main_win.progress_win.add_task(task)
    pmaster.add_task(task)
    return task


def save_settings():
    settings['hash_cache'] = dict()
    for path, info in util.HASH_CACHE.items():
        # Skip deleted files
        if os.path.exists(path):
            settings['hash_cache'][path] = info
    
    for mod in settings['cmdlines'].copy():
        if mod != '#default' and mod not in installed.mods:
            del settings['cmdlines'][mod]
    
    with open(os.path.join(settings_path, 'settings.pick'), 'wb') as stream:
        pickle.dump(settings, stream, 2)


def show_tab(a, b, tab):
    global main_win
    return

    # TODO: If we're in Nebula mode, we'll have to open the traditional window for this.
    main_win.tabs.setCurrentIndex(tab)
    main_win.activateWindow()

    
def go_to_hlp(a, b, tab):
    QtGui.QDesktopServices.openUrl("http://www.hard-light.net/")


def select_fs2_path(interact=True):
    if interact:
        if settings['fs2_path'] is None:
            path = os.path.expanduser('~')
        else:
            path = settings['fs2_path']
        
        fs2_path = QtGui.QFileDialog.getExistingDirectory(main_win.win, 'Please select your FS2 directory.', path)
    else:
        fs2_path = settings['fs2_path']

    if fs2_path is not None and os.path.isdir(fs2_path):
        settings['fs2_path'] = os.path.abspath(fs2_path)

        if sys.platform.startswith('win'):
            pattern = 'fs2_open_*.exe'
        else:
            pattern = 'fs2_open_*'

        bins = glob.glob(os.path.join(fs2_path, pattern))
        if len(bins) == 1:
            # Found only one binary, select it by default.

            settings['fs2_bin'] = os.path.basename(bins[0])
        elif len(bins) > 1:
            # Let the user choose.

            select_win = util.init_ui(Ui_SelectList(), util.QDialog(main_win.win))
            has_default = False
            bins.sort()

            for i, path in enumerate(bins):
                path = os.path.basename(path)
                if path.endswith(('.map', '.pdb')):
                    continue

                select_win.listWidget.addItem(path)

                if path.endswith('.exe'):
                    path = path[:-4]

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

        main_win.check_fso()


def get_fso_flags():
    global fso_flags

    if settings['fs2_bin'] is None:
        return

    if fso_flags is not None and fso_flags[0] == settings['fs2_bin']:
        return fso_flags[1]

    fs2_bin = os.path.join(settings['fs2_path'], settings['fs2_bin'])
    if not os.path.isfile(fs2_bin):
        return

    flags_path = os.path.join(settings['fs2_path'], 'flags.lch')
    mode = os.stat(fs2_bin).st_mode
    
    if mode & stat.S_IXUSR != stat.S_IXUSR:
        # Make it executable.
        os.chmod(fs2_bin, mode | stat.S_IXUSR)
    
    rc = util.call([fs2_bin, '-get_flags'], cwd=settings['fs2_path'])
    flags = None

    if rc != 1 and rc != 0:
        logging.error('Failed to run FSO! (Exit code was %d)', rc)
    elif not os.path.isfile(flags_path):
        logging.error('Could not find the flags file "%s"!', flags_path)
    else:
        with open(flags_path, 'rb') as stream:
            flags = util.FlagsReader(stream)

    if flags is None:
        QtGui.QMessageBox.critical(app.activeWindow(), 'fs2mod-py', 'I can\'t run FS2 Open! Are you sure you selected the right file?')

    fso_flags = (settings['fs2_bin'], flags)
    return flags


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


def run_mod(mod):
    global installed

    if mod is None:
        mod = repo.Mod()
    
    modpath = util.ipath(os.path.join(settings['fs2_path'], mod.folder))
    ini = None
    modfolder = None
    
    def check_install():
        if not os.path.isdir(modpath) or mod.mid not in installed.mods:
            QtGui.QMessageBox.critical(app.activeWindow(), 'Error', 'Failed to install "%s"! Check the log for more information.' % (mod.title))
        else:
            run_mod(mod)
    
    if settings['fs2_bin'] is None:
        select_fs2_path()

        if settings['fs2_bin'] is None:
            QtGui.QMessageBox.critical(app.activeWindow(), 'Error', 'I couldn\'t find a FS2 executable. Can\'t run FS2!!')
            return
    
    if mod.title != '' and (not os.path.isdir(modpath) or mod.mid not in installed.mods):
        deps = settings['mods'].process_pkg_selection(mod.resolve_deps())
        titles = [pkg.name for pkg in deps if not installed.is_installed(pkg)]

        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Question)
        msg.setText('You don\'t have %s, yet. Shall I install it?' % (mod.title))
        msg.setInformativeText('%s will be installed.' % (', '.join(titles)))
        msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        msg.setDefaultButton(QtGui.QMessageBox.Yes)
        
        if msg.exec_() == QtGui.QMessageBox.Yes:
            task = InstallTask(deps)
            task.done.connect(check_install)
            run_task(task)
        
        return
    
    # Look for the mod.ini
    for item in mod.filelist:
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
            for item in mod.filelist:
                if item.lower().endswith('.vp'):
                    modfolder = item.split('/')[0]
                    break
        else:
            modfolder = mod.folder.split('/')[0]
    
    if modfolder == '':
        modfolder = None

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
    
    if mod.mid in settings['cmdlines']:
        # We have a saved cmdline for this mod.
        cmdline = settings['cmdlines'][mod.mid][:]
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

                    if len(cmdline) <= i + 1:
                        cmdline.append(modfolder)
                    else:
                        cmdline[i + 1] = modfolder
                    break
    
    if modfolder is None:
        if mod_found:
            cmdline.remove('-mod')
            cmdline.remove(modfolder)
    elif not mod_found:
        cmdline.append('-mod')
        cmdline.append(modfolder)
    
    if not os.path.isfile(path):
        basep = os.path.dirname(path)
        if not os.path.isdir(basep):
            os.makedirs(basep)

    try:
        with open(path, 'w') as stream:
            stream.write(' '.join(cmdline))
    except:
        logging.exception('Failed to modify "%s". Not starting FS2!!', path)
        
        QtGui.QMessageBox.critical(app.activeWindow(), 'Error', 'Failed to edit "%s"! I can\'t change the current mod!' % path)
    else:
        run_fs2()


def ql_add_repo(a, b, tab):
    return

    # TODO: Fix this in Nebula mode.
    main_win.tabs.setCurrentIndex(tab)
    main_win.activateWindow()
    add_repo()


def show_fs2settings():
    SettingsWindow(None)


def switch_ui_mode(nmode):
    global main_win

    old_win = main_win
    if nmode == 'nebula':
        main_win = NebulaWindow()
    else:
        main_win = MainWindow()

    main_win.open()
    old_win.close()


def main(app_):
    global VERSION, app, settings, installed, pmaster, main_win, progress_win, unity_launcher, browser_ctrl

    app = app_
    
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
        if 's_version' not in settings:
            settings['repos'] = defaults['repos']
            settings['s_version'] = 1
        
        del defaults
    else:
        # Most recent settings version
        settings['s_version'] = 1
    
    if settings['hash_cache'] is not None:
        util.HASH_CACHE = settings['hash_cache']

    util.DL_POOL.set_capacity(settings['max_downloads'])

    installed = repo.InstalledRepo(settings.get('installed_mods', []))
    pmaster.start_workers(10)
    
    if os.path.isfile('hlp.png'):
        app.setWindowIcon(QtGui.QIcon('hlp.png'))

    if not util.test_7z():
        QtGui.QMessageBox.critical(None, 'Error', 'I can\'t find "7z"! Please install it and run this program again.', QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
        return

    if os.path.isfile('commit'):
        with open('commit', 'r') as data:
            VERSION += '-' + data.read().strip()

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
    
    if settings['ui_mode'] == 'nebula':
        main_win = NebulaWindow()
    else:
        main_win = MainWindow()

    QtCore.QTimer.singleShot(1, api.setup_ipc)
    QtCore.QTimer.singleShot(1, lambda: run_task(CheckUpdateTask()))

    main_win.open()
    app.exec_()
    
    save_settings()
    api.shutdown_ipc()
