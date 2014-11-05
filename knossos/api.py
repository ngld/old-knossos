## Copyright 2014 Knossos authors, see NOTICE file
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
import json
import threading
import stat
import subprocess
import time
import shlex
import glob
import pickle

from . import uhf
uhf(__name__)

from . import center, util, repo
from .qt import QtCore, QtGui
from .tasks import run_task, CheckUpdateTask, CheckTask, FetchTask, InstallTask, UninstallTask
from .ui.select_list import Ui_Dialog as Ui_SelectList
from .windows import NebulaWindow, MainWindow, HellWindow, SettingsWindow
from .repo import ModNotFound
from .ipc import IPCComm

ipc_block = None
fs2_watcher = None


class Fs2Watcher(threading.Thread):
    _params = None
    _key_layout = None
    
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

        if center.settings['keyboard_layout'] != 'default':
            self._params.append('-keyboard_layout')
            self._params.append(center.settings['keyboard_layout'])
        
        fs2_bin = os.path.join(center.settings['fs2_path'], center.settings['fs2_bin'])
        mode = os.stat(fs2_bin).st_mode
        if mode & stat.S_IXUSR != stat.S_IXUSR:
            # Make it executable.
            os.chmod(fs2_bin, mode | stat.S_IXUSR)

        if center.settings['keyboard_setxkbmap']:
            self.set_us_layout()
        
        logging.debug('Launching FS2: %s', [fs2_bin] + self._params)
        p = subprocess.Popen([fs2_bin] + self._params, cwd=center.settings['fs2_path'])

        time.sleep(0.3)
        if p.poll() is not None:
            self.revert_layout()
            center.signals.fs2_failed.emit(p.returncode)
            self.failed_msg(p)
            return
        
        center.signals.fs2_launched.emit()
        p.wait()
        self.revert_layout()
        center.signals.fs2_quit.emit()
    
    @util.run_in_qt
    def failed_msg(self, p):
        msg = 'Starting FS2 Open (%s) failed! (return code: %d)' % (os.path.join(center.settings['fs2_path'], center.settings['fs2_bin']), p.returncode)
        QtGui.QMessageBox.critical(center.app.activeWindow(), 'Failed', msg)

    def set_us_layout(self):
        key_layout = util.check_output(['setxkbmap', '-query'])
        self._key_layout = key_layout.decode('utf8').splitlines()[2].split(':')[1].strip()

        util.call(['setxkbmap', '-layout', 'us'])

    def revert_layout(self):
        if self._key_layout is not None:
            util.call(['setxkbmap', '-layout', self._key_layout])


def save_settings():
    center.settings['hash_cache'] = dict()
    for path, info in util.HASH_CACHE.items():
        # Skip deleted files
        if os.path.exists(path):
            center.settings['hash_cache'][path] = info
    
    for mod in center.settings['cmdlines'].copy():
        if mod != '#default' and mod not in center.installed.mods:
            del center.settings['cmdlines'][mod]
    
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

        if sys.platform.startswith('win'):
            pattern = 'fs2_open_*.exe'
        else:
            pattern = 'fs2_open_*'

        bins = glob.glob(os.path.join(fs2_path, pattern))
        if len(bins) == 1:
            # Found only one binary, select it by default.

            center.settings['fs2_bin'] = os.path.basename(bins[0])
        elif len(bins) > 1:
            # Let the user choose.

            select_win = util.init_ui(Ui_SelectList(), util.QDialog(center.main_win.win))
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
                center.settings['fs2_bin'] = select_win.listWidget.currentItem().text()
        else:
            center.settings['fs2_bin'] = None

        center.main_win.check_fso()


def get_fso_flags():
    global fso_flags

    if center.settings['fs2_bin'] is None:
        return

    if center.fso_flags is not None and center.fso_flags[0] == center.settings['fs2_bin']:
        return center.fso_flags[1]

    fs2_bin = os.path.join(center.settings['fs2_path'], center.settings['fs2_bin'])
    if not os.path.isfile(fs2_bin):
        return

    flags_path = os.path.join(center.settings['fs2_path'], 'flags.lch')
    mode = os.stat(fs2_bin).st_mode
    
    if mode & stat.S_IXUSR != stat.S_IXUSR:
        # Make it executable.
        os.chmod(fs2_bin, mode | stat.S_IXUSR)
    
    rc = util.call([fs2_bin, '-get_flags'], cwd=center.settings['fs2_path'])
    flags = None

    if rc != 1 and rc != 0:
        logging.error('Failed to run FSO! (Exit code was %d)', rc)
    elif not os.path.isfile(flags_path):
        logging.error('Could not find the flags file "%s"!', flags_path)
    else:
        with open(flags_path, 'rb') as stream:
            flags = util.FlagsReader(stream)

    if flags is None:
        QtGui.QMessageBox.critical(center.app.activeWindow(), 'Knossos', 'I can\'t run FS2 Open! Are you sure you selected the right file?')

    fso_flags = (center.settings['fs2_bin'], flags)
    return flags


def run_fs2(params=None):
    global fs2_watcher
    
    if fs2_watcher is None or not fs2_watcher.is_alive():
        fs2_watcher = Fs2Watcher(params)
        return True
    else:
        return False


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


def run_mod(mod):
    global installed

    if mod is None:
        mod = repo.Mod()
    
    modpath = util.ipath(os.path.join(center.settings['fs2_path'], mod.folder))
    ini = None
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
        deps = center.settings['mods'].process_pkg_selection(mod.resolve_deps())
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

    # Look for the mod.ini
    for item in mod.get_files():
        if item['filename'].lower() == 'mod.ini':
            ini = item['filename']
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
                        primlist = line[1].replace(',,', ',').strip(',').split(',')
                    elif line[0] in ('secondrylist', 'secondarylist'):
                        seclist = line[1].replace(',,', ',').strip(',').split(',')
        except:
            logging.exception('Failed to read %s!', os.path.join(modpath, ini))
        
        if ini == 'mod.ini':
            ini = os.path.basename(modpath) + '/' + ini

        try:
            local_deps = mod.resolve_deps()
            rem_deps = [center.installed.query(pkg) for pkg in local_deps]
        except repo.ModNotFound:
            logging.exception('Failed to resolve the dependencies of mod "%s"! I won\'t be able to generate a correct -mod list.', mod.title)
        else:
            dir_map = {}
            local_mods = {}
            rem_mods = {}

            for pkg in local_deps:
                mod = pkg.get_mod()
                local_mods[mod.mid] = mod.folder

            for pkg in rem_deps:
                mod = pkg.get_mod()
                rem_mods[mod.mid] = mod.folder

            for mid, folder in local_mods.items():
                dir_map[rem_mods[mid]] = folder

            for i, item in enumerate(primlist):
                if item in dir_map:
                    primlist[i] = dir_map[item]

            for i, item in enumerate(seclist):
                if item in dir_map:
                    seclist[i] = dir_map[item]

            del local_mods, rem_mods, dir_map

        # Build the whole list for -mod
        mods = primlist + [os.path.dirname(ini)] + seclist
    else:
        # No mod.ini found, look for the first subdirectory then.
        if mod.folder in ('', '.'):
            # Well, this is no ordinary mod. No -mod flag for you!
            pass
        else:
            mods = [mod.folder]
    
    m = []
    for item in mods:
        if item.strip() != '':
            m.append(os.path.basename(util.ipath(os.path.join(center.settings['fs2_path'], item))))
    
    mods = m
    del m
    mod_found = False
    
    # Look for the cmdline path.
    if sys.platform.startswith('linux'):
        # TODO: What about Mac OS ?
        path = os.path.expanduser('~/.fs2_open')
    else:
        path = center.settings['fs2_path']
    
    path = os.path.join(path, 'data/cmdline_fso.cfg')
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
                mod_found = True

                if len(cmdline) <= i + 1:
                    cmdline.apppend(','.join(mods))
                else:
                    cmdline[i + 1] = ','.join(mods)
                break
    
    if len(mods) == 0:
        if mod_found:
            cmdline.remove('-mod')
            cmdline.remove('')
    elif not mod_found:
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
    if center.settings['mods'] is None:
        QtGui.QMessageBox.critical(None, 'Knossos', 'Hmm... I never got a mod list. Get a coder!')
        return None
    else:
        try:
            return center.settings['mods'].query(mid, version)
        except ModNotFound:
            QtGui.QMessageBox.critical(None, 'Knossos', 'Mod "%s" could not be found!' % mid)
            return None


def install_mods(mods):
    pkgs = []
    for mod in mods:
        pkgs.extend(mod.resolve_deps())

    install_pkgs(pkgs, ', '.join([mod.name for mod in mods]))


def install_pkgs(pkgs, name=None, cb=None):
    repo = center.settings['mods']

    try:
        pkgs = [repo.query(pkg) for pkg in pkgs]
    except ModNotFound:
        logging.exception('Failed to find one of the packages!')
        QtGui.QMessageBox.critical(center.app.activateWindow(), 'Knossos', 'Failed to find one of the packages! I can\'t accept this install request.')
        return

    deps = center.settings['mods'].process_pkg_selection(pkgs)
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
    msg.setInformativeText('%s will be installed.' % (', '.join(titles)))
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
    elif nmode == 'nebula':
        center.main_win = NebulaWindow()
    else:
        center.main_win = MainWindow()

    center.main_win.open()
    old_win.close()


#########
# Tools #
#########


def install_scheme_handler(interactive=True):
    logging.info('Installing scheme handler...')

    from . import launcher
    my_cmd = launcher.get_cmd()
    
    if sys.platform.startswith('win'):
        settings = QtCore.QSettings('HKEY_CLASSES_ROOT\\fso', QtCore.QSettings.NativeFormat)
        settings.setFallbacksEnabled(False)

        settings.setValue('Default', 'URL:Knossos protocol')
        settings.setValue('URL Protocol', '')
        settings.setValue('DefaultIcon/Default', '"' + launcher.get_file_path('hlp.ico') + ',1"')

        my_cmd.append('%1')
        my_path = ' '.join(['"' + p + '"' for p in my_cmd])
        
        settings.setValue('shell/open/command/Default', my_path)

        # Check
        # FIXME: Is there any better way to detect whether this worked or not?

        settings.sync()
        settings = QtCore.QSettings('HKEY_CLASSES_ROOT\\fso', QtCore.QSettings.NativeFormat)
        settings.setFallbacksEnabled(False)

        if settings.value('shell/open/command/Default') != my_path:
            if interactive:
                QtGui.QMessageBox.critical(None, 'Knossos', 'I probably failed to install the scheme handler.\nRun me as administrator and try again.')

            return
        
    elif sys.platform.startswith('linux'):
        tpl_desktop = r"""[Desktop Entry]
Name=Knossos
Exec={PATH} %U
Icon={ICON_PATH}
Type=Application
Terminal=false
MimeType=x-scheme-handler/fso;
"""

        tpl_mime_type = 'x-scheme-handler/fso=Knossos.desktop;'

        applications_path = os.path.expanduser('~/.local/share/applications/')
        desktop_file = applications_path + 'Knossos.desktop'
        mime_types_file = applications_path + 'mimeapps.list'
        my_path = ' '.join([shlex.quote(p) for p in my_cmd])
        
        tpl_desktop = tpl_desktop.replace('{PATH}', my_path)
        tpl_desktop = tpl_desktop.replace('{ICON_PATH}', launcher.get_file_path('hlp.png'))
        
        if not os.path.isdir(applications_path):
            os.makedirs(applications_path)

        with open(desktop_file, 'w') as output_file:
            output_file.write(tpl_desktop)
        
        found = False
        if os.path.isfile(mime_types_file):
            with open(mime_types_file, 'r') as lines:
                for line in lines:
                    if tpl_mime_type in line:
                        found = True
                        break
        
        if not found:
            with open(mime_types_file, 'a') as output_file:
                output_file.write(tpl_mime_type)

    if interactive:
        QtGui.QMessageBox.information(None, 'Knossos', 'Done!')


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

    if center.settings['update_notify']:
        run_task(CheckUpdateTask())

    if center.settings['fs2_path'] is not None:
        run_task(CheckTask())
