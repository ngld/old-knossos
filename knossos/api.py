## Copyright 2015 Knossos authors, see NOTICE file
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
import os
import logging
import json
import shlex
import glob
import pickle

from . import uhf
uhf(__name__)

from . import center, util, repo, integration
from .qt import QtGui
from .tasks import run_task, CheckUpdateTask, FetchTask, InstallTask, UninstallTask
from .ui.select_list import Ui_Dialog as Ui_SelectList
from .windows import QDialog, HellWindow, SettingsWindow
from .repo import ModNotFound
from .ipc import IPCComm
from .runner import run_fs2, run_fs2_silent

ipc_block = None


def save_settings():
    center.settings['hash_cache'] = dict()
    for path, info in util.HASH_CACHE.items():
        # Skip deleted files
        if os.path.exists(path):
            center.settings['hash_cache'][path] = info
    
    for mod in center.settings['cmdlines'].copy():
        if mod != '#default' and mod not in center.installed.mods:
            del center.settings['cmdlines'][mod]

    center.settings['pins'] = center.installed.pins
    
    with open(os.path.join(center.settings_path, 'settings.pick'), 'wb') as stream:
        pickle.dump(center.settings, stream, 2)


def select_fs2_path(interact=True):
    if interact:
        if center.settings['fs2_path'] is None:
            path = os.path.expanduser('~')
        else:
            path = center.settings['fs2_path']
        
        fs2_path = QtGui.QFileDialog.getExistingDirectory(center.main_win.win, 'Please select your FS2 directory.', path)
    else:
        fs2_path = center.settings['fs2_path']

    if fs2_path is not None and os.path.isdir(fs2_path):
        center.settings['fs2_path'] = os.path.abspath(fs2_path)

        bins = get_executables()
        if len(bins) == 1:
            # Found only one binary, select it by default.

            center.settings['fs2_bin'] = bins[0][1]
        elif len(bins) > 1:
            # Let the user choose.

            select_win = util.init_ui(Ui_SelectList(), QtGui.QDialog(center.main_win.win))
            has_default = False
            bins.sort()

            for i, path in enumerate(bins):
                select_win.listWidget.addItem(path[0])

                if not has_default and 'DEBUG' not in path[0]:
                    # Select the first non-debug build as default.

                    select_win.listWidget.setCurrentRow(i)
                    has_default = True

            select_win.listWidget.itemDoubleClicked.connect(select_win.accept)
            select_win.okButton.clicked.connect(select_win.accept)
            select_win.cancelButton.clicked.connect(select_win.reject)

            if select_win.exec_() == QtGui.QDialog.Accepted:
                center.settings['fs2_bin'] = bins[select_win.listWidget.currentRow()][1]

            select_win.deleteLater()
        else:
            center.settings['fs2_bin'] = None

        center.main_win.check_fso()
        center.signals.fs2_path_changed.emit()

        if center.settings['fs2_bin'] is not None:
            center.signals.fs2_bin_changed.emit()


def get_fso_flags():
    global fso_flags

    if center.settings['fs2_bin'] is None:
        return None

    if center.fso_flags is not None and center.fso_flags[0] == center.settings['fs2_bin']:
        return center.fso_flags[1]

    fs2_bin = os.path.join(center.settings['fs2_path'], center.settings['fs2_bin'])
    if not os.path.isfile(fs2_bin):
        return None

    if sys.platform.startswith('win'):
        flags_path = os.path.join(center.settings['fs2_path'], os.path.dirname(center.settings['fs2_bin']), 'flags.lch')
    else:
        flags_path = os.path.join(center.settings['fs2_path'], 'flags.lch')
    
    rc = run_fs2_silent(['-get_flags'])
    
    flags = None

    if rc != 1 and rc != 0:
        logging.error('Failed to run FSO! (Exit code was %d)', rc)
    elif not os.path.isfile(flags_path):
        logging.error('Could not find the flags file "%s"!', flags_path)
    else:
        with open(flags_path, 'rb') as stream:
            flags = util.FlagsReader(stream)

    center.fso_flags = (center.settings['fs2_bin'], flags)
    return flags


def get_executables():
    exes = []
    fs2_path = center.settings['fs2_path']

    for mid, mvs in center.installed.mods.items():
        for mod in mvs:
            for pkg in mod.packages:
                for item in pkg.executables:
                    name = mod.title + ' ' + item.get('version', '')
                    if item.get('debug', False):
                        name += ' (DEBUG)'

                    path = os.path.join(mod.folder, item['file'])
                    exes.append((name, path))

    if fs2_path is not None and os.path.isdir(fs2_path):
        fs2_path = os.path.abspath(fs2_path)
        if sys.platform == 'darwin':
            for app in glob.glob(os.path.join(fs2_path, '*.app')):
                name = os.path.basename(app)
                exes.append((name, os.path.join(name, 'Contents', 'MacOS', name[:-4])))
        else:
            bins = glob.glob(os.path.join(fs2_path, 'fs2_open_*'))
            
            for path in bins:
                path = os.path.basename(path)

                if not path.endswith(('.map', '.pdb')):
                    exes.append((path, path))

    return exes


def fetch_list():
    return run_task(FetchTask())


def show_fs2settings():
    SettingsWindow(None)


def get_cmdline(mod):
    if mod is None:
        return center.settings['cmdlines'].get('#default', [])[:]

    if mod.cmdline != '':
        return shlex.split(mod.cmdline)
    elif mod.mid in center.settings['cmdlines']:
        return center.settings['cmdlines'][mod.mid][:]
    else:
        return center.settings['cmdlines'].get('#default', [])[:]


def get_fso_profile_path():
    if sys.platform.startswith('linux'):
        return os.path.expanduser('~/.fs2_open')
    elif sys.platform == 'darwin':
        return os.path.expanduser('~/Library/FS2_Open')
    else:
        return center.settings['fs2_path']


def run_mod(mod):
    global installed

    if mod is None:
        mod = repo.Mod()
    
    modpath = util.ipath(os.path.join(center.settings['fs2_path'], mod.folder))
    mods = []
    
    def check_install():
        if not os.path.isdir(modpath) or mod.mid not in center.installed.mods:
            QtGui.QMessageBox.critical(center.app.activeWindow(), 'Error', 'Failed to install "%s"! Check the log for more information.' % (mod.title))
        else:
            run_mod(mod)
    
    if center.settings['fs2_bin'] is None:
        select_fs2_path()

        if center.settings['fs2_bin'] is None:
            QtGui.QMessageBox.critical(center.app.activeWindow(), 'Error', 'I couldn\'t find a FS2 executable. Can\'t run FS2!!')
            return

    try:
        inst_mod = center.installed.query(mod)
    except repo.ModNotFound:
        inst_mod = None
    
    if inst_mod is None:
        deps = center.mods.process_pkg_selection(mod.resolve_deps())
        titles = [pkg.name for pkg in deps if not center.installed.is_installed(pkg)]

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

    try:
        mods = mod.get_mod_flag()
    except repo.ModNotFound as exc:
        QtGui.QMessageBox.critical(None, 'Knossos', 'Sorry, I can\'t start this mod because its dependency "%s" is missing!' % exc.mid)
        return
    
    mod_flag_found = False

    if mods is None:
        return
    
    # Look for the cmdline path.
    path = os.path.join(get_fso_profile_path(), 'data/cmdline_fso.cfg')
    cmdline = get_cmdline(mod)
    
    if len(cmdline) == 0:
        # Read the current cmdline.
        cmdline = []
        if os.path.exists(path):
            try:
                with open(path, 'r') as stream:
                    cmdline = shlex.split(stream.read().strip())
            except:
                logging.exception('Failed to read "%s", assuming empty cmdline.', path)
        
        for i, part in enumerate(cmdline):
            if part.strip() == '-mod':
                mod_flag_found = True

                if len(cmdline) <= i + 1:
                    cmdline.apppend(','.join(mods))
                else:
                    cmdline[i + 1] = ','.join(mods)
                break
    
    if len(mods) == 0:
        if mod_flag_found:
            cmdline.remove('-mod')
            cmdline.remove('')
    elif not mod_flag_found:
        cmdline.append('-mod')
        cmdline.append(','.join(mods))
    
    if not os.path.isfile(path):
        basep = os.path.dirname(path)
        if not os.path.isdir(basep):
            os.makedirs(basep)

    try:
        with open(path, 'w') as stream:
            stream.write(' '.join([shlex.quote(p) for p in cmdline]))
    except:
        logging.exception('Failed to modify "%s". Not starting FS2!!', path)
        
        QtGui.QMessageBox.critical(center.app.activeWindow(), 'Error', 'Failed to edit "%s"! I can\'t change the current mod!' % path)
    else:
        logging.info('Starting mod "%s" with cmdline "%s".', mod.title, cmdline)
        run_fs2()

##############
# Public API #
##############


def is_fso_installed():
    fs2_path = center.settings['fs2_path']
    if fs2_path is not None:
        fs2_bin = os.path.join(fs2_path, center.settings['fs2_bin'])

    return fs2_path is not None and fs2_bin is not None and os.path.isdir(fs2_path) and os.path.isfile(fs2_bin)


def get_mod(mid, version=None):
    if center.mods is None:
        QtGui.QMessageBox.critical(None, 'Knossos', 'Hmm... I never got a mod list. Get a coder!')
        return None
    else:
        try:
            return center.mods.query(mid, version)
        except ModNotFound:
            QtGui.QMessageBox.critical(None, 'Knossos', 'Mod "%s" could not be found!' % mid)
            return None


def install_mods(mods):
    pkgs = []
    for mod in mods:
        pkgs.extend(mod.resolve_deps())

    install_pkgs(pkgs, ', '.join([mod.name for mod in mods]))


def install_pkgs(pkgs, name=None, cb=None):
    repo = center.mods

    try:
        pkgs = [repo.query(pkg) for pkg in pkgs]
    except ModNotFound:
        logging.exception('Failed to find one of the packages!')
        QtGui.QMessageBox.critical(center.app.activateWindow(), 'Knossos', 'Failed to find one of the packages! I can\'t accept this install request.')
        return

    deps = center.mods.process_pkg_selection(pkgs)
    titles = [pkg.name + ' (%s)' % pkg.get_mod().version for pkg in deps if not center.installed.is_installed(pkg)]

    if name is None:
        name = 'these packages'

    msg = QtGui.QMessageBox()
    msg.setIcon(QtGui.QMessageBox.Question)
    msg.setText('Do you really want to install %s?' % name)
    msg.setInformativeText('%s will be installed.' % (', '.join(titles)))
    msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
    msg.setDefaultButton(QtGui.QMessageBox.Yes)
    
    if msg.exec_() == QtGui.QMessageBox.Yes:
        task = InstallTask(deps)
        if cb is not None:
            task.done.connect(cb)

        run_task(task)
        return True
    else:
        return False


def uninstall_pkgs(pkgs, name=None, cb=None):
    titles = [pkg.name for pkg in pkgs if center.installed.is_installed(pkg)]

    if name is None:
        name = 'these packages'

    msg = QtGui.QMessageBox()
    msg.setIcon(QtGui.QMessageBox.Question)
    msg.setText('Do you really want to uninstall %s?' % name)
    msg.setInformativeText('%s will be removed.' % (', '.join(titles)))
    msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
    msg.setDefaultButton(QtGui.QMessageBox.Yes)
    
    if msg.exec_() == QtGui.QMessageBox.Yes:
        task = UninstallTask(pkgs)
        if cb is not None:
            task.done.connect(cb)

        run_task(task)
        return True
    else:
        return False


def switch_ui_mode(nmode):
    old_win = center.main_win
    if nmode == 'hell':
        center.main_win = HellWindow()
    else:
        logging.error('Unknown UI mode "%s"! (Maybe you tried to use a legacy UI...)' % nmode)

    center.main_win.open()
    old_win.close()


#########
# Tools #
#########


def install_scheme_handler(interactive=True):
    logging.info('Installing scheme handler...')

    try:
        if integration.current.install_scheme_handler():
            if interactive:
                QtGui.QMessageBox.information(None, 'Knossos', 'Done!')
            return
    except:
        logging.exception('Failed to install the scheme handler!')
    
    QtGui.QMessageBox.critical(None, 'Knossos', 'I probably failed to install the scheme handler.\nRun me as administrator and try again.')


def setup_ipc():
    global ipc_block

    ipc_block = IPCComm(center.settings_path)
    ipc_block.messageReceived.connect(handle_ipc)
    ipc_block.listen()


def shutdown_ipc():
    global ipc_block

    ipc_block.close()


def handle_ipc(msg):
    msg = msg.data().decode('utf8', 'ignore').strip()

    try:
        msg = json.loads(msg)
    except:
        logging.exception('Failed to parse IPC message %s.', msg)
        return

    if msg[0] == 'focus':
        center.main_win.win.activateWindow()
        center.main_win.win.raise_()
    elif msg[0] == 'mode':
        if msg[1] in ('traditional', 'nebula'):
            switch_ui_mode(msg[1])
    elif msg[0] == 'run':
        mod = get_mod(msg[1])

        if mod is not None:
            run_mod(mod)
    elif msg[0] == 'install':
        mod = get_mod(msg[1])
        pkgs = []

        if len(msg) > 2:
            for pname in msg[2:]:
                for pkg in mod.packages:
                    if pkg.name == pname:
                        pkgs.append(pkg)

        center.main_win.win.activateWindow()

        if mod.mid not in center.installed.mods:
            install_pkgs(mod.resolve_deps() + pkgs, mod.name)
        else:
            QtGui.QMessageBox.information(center.main_win.win, 'Knossos', 'Mod "%s" is already installed!' % (mod.name))
    elif msg[0] == 'settings':
        center.main_win.win.activateWindow()

        if len(msg) == 1 or msg[1] == '':
            center.main_win.show_fso_settings()
        else:
            mod = get_mod(msg[1])

            if mod is None or mod.mid not in center.installed.mods:
                if mod is None:
                    name = msg[1]
                else:
                    name = mod.title
                QtGui.QMessageBox.information(center.main_win.win, 'Knossos', 'Mod "%s" is not yet installed!' % (name))
            else:
                SettingsWindow(mod)
    else:
        QtGui.QMessageBox.critical(center.main_win.win, 'Knossos', 'The action "%s" is unknown!' % (msg[0]))


def init_self():
    setup_ipc()
    center.main_win.check_fso()

    if center.settings['update_notify'] and not center.VERSION.endswith('-dev'):
        run_task(CheckUpdateTask())
