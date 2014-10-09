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

import sys
import os
import logging
import json

from .qt import QtCore, QtGui
from .tasks import InstallTask, UninstallTask
from .windows import SettingsWindow
from .repo import ModNotFound
from .ipc import IPCComm
import manager


ipc_block = None

##############
# Public API #
##############


def is_fso_installed():
    fs2_path = manager.settings['fs2_path']
    if fs2_path is not None:
        fs2_bin = os.path.join(fs2_path, manager.settings['fs2_bin'])

    return fs2_path is not None and fs2_bin is not None and os.path.isdir(fs2_path) and os.path.isfile(fs2_bin)


def get_mod(mid, version=None):
    if manager.settings['mods'] is None:
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Hmm... I never got a mod list. Get a coder!')
        return None
    else:
        try:
            return manager.settings['mods'].query(mid, version)
        except ModNotFound:
            QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Mod "%s" could not be found!' % mid)
            return None


def install_mods(mods):
    pkgs = []
    for mod in mods:
        pkgs.extend(mod.resolve_deps())

    install_pkgs(pkgs, ', '.join([mod.name for mod in mods]))


def install_pkgs(pkgs, name=None, cb=None):
    deps = manager.settings['mods'].process_pkg_selection(pkgs)
    titles = [pkg.name for pkg in deps if not manager.installed.is_installed(pkg)]

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

        manager.run_task(task)
        return True
    else:
        return False


def uninstall_pkgs(pkgs, name=None, cb=None):
    titles = [pkg.name for pkg in pkgs if manager.installed.is_installed(pkg)]

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

        manager.run_task(task)
        return True
    else:
        return False

#########
# Tools #
#########


def install_scheme_handler(interactive=True):
    logging.info('Installing scheme handler...')

    if hasattr(sys, 'frozen'):
        my_path = os.path.abspath(sys.executable)
    else:
        my_path = os.path.abspath(__file__)
            
    if sys.platform.startswith('win'):
        settings = QtCore.QSettings('HKEY_CLASSES_ROOT\\fso', QtCore.QSettings.NativeFormat)
        settings.setFallbacksEnabled(False)

        settings.setValue('Default', 'URL:fs2mod-py protocol')
        settings.setValue('URL Protocol', '')
        settings.setValue('DefaultIcon/Default', '"' + my_path + ',1"')
        
        settings.setValue('shell/open/command/Default', '"' + my_path + '" "%1"')

        # Check
        # FIXME: Is there any better way to detect whether this worked or not?

        settings.sync()
        settings = QtCore.QSettings('HKEY_CLASSES_ROOT\\fso', QtCore.QSettings.NativeFormat)
        settings.setFallbacksEnabled(False)

        if settings.value('shell/open/command/Default') != '"' + my_path + '" "%1"':
            if interactive:
                QtGui.QMessageBox.critical(None, 'fs2mod-py', 'I probably failed to install the scheme handler.\nRun me as administrator and try again.')

            return
        
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

    if interactive:
        QtGui.QMessageBox.information(None, 'fs2mod-py', 'Done!')


def setup_ipc():
    global ipc_block

    ipc_block = IPCComm(manager.settings_path)
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
        manager.main_win.win.activateWindow()
    elif msg[0] == 'mode':
        if msg[1] in ('traditional', 'nebula'):
            manager.switch_ui_mode(msg[1])
    elif msg[0] == 'run':
        mod = get_mod(msg[1])

        if mod is not None:
            manager.run_mod(mod)
    elif msg[0] == 'install':
        mod = get_mod(msg[1])
        pkgs = []

        if len(msg) > 2:
            for pname in msg[2:]:
                for pkg in mod.packages:
                    if pkg.name == pname:
                        pkgs.append(pkg)

        manager.main_win.win.activateWindow()

        if mod.mid not in manager.installed.mods:
            install_pkgs(mod.resolve_deps() + pkgs, mod.name)
        else:
            QtGui.QMessageBox.information(manager.main_win.win, 'fs2mod-py', 'Mod "%s" is already installed!' % (mod.name))
    elif msg[0] == 'settings':
        manager.main_win.win.activateWindow()

        if len(msg) == 1 or msg[1] == '':
            manager.main_win.show_fso_settings()
        else:
            mod = get_mod(msg[1])

            if mod is None or mod.mid not in manager.installed.mods:
                if mod is None:
                    name = msg[1]
                else:
                    name = mod.title
                QtGui.QMessageBox.information(manager.main_win.win, 'fs2mod-py', 'Mod "%s" is not yet installed!' % (name))
            else:
                SettingsWindow(mod)
    else:
        QtGui.QMessageBox.critical(manager.main_win.win, 'fs2mod-py', 'The action "%s" is unknown!' % (msg[0]))
