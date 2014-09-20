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
import functools
import logging
import json
import time
import uuid
from six.moves.urllib import parse as urlparse

from .qt import QtCore, QtGui, QtNetwork
from .tasks import InstallTask
from .windows import SettingsWindow
from .repo import ModNotFound
import manager


ipc_block = None

######################
# IPC Implementation #
######################


class IPCComm(QtCore.QObject):
    _path = None
    _server = None
    _conn_pool = None
    _socket = None
    _queue = None
    messageReceived = QtCore.Signal(QtCore.QByteArray)

    def __init__(self, path):
        super(IPCComm, self).__init__()

        self._path = path
        self._queue = []

    def get_file(self):
        return os.path.join(self._path, 'ipcinfo')

    def server_exists(self):
        # TODO: Maybe we should check if the server is running?
        return os.path.isfile(self.get_file())

    def listen(self):
        if self._server is not None:
            raise Exception('IPCComm() is already listening!')

        name = 'fs2mod-' + str(uuid.uuid4())
        self._server = QtNetwork.QLocalServer()
        if not self._server.listen(name):
            msg = self._server.errorString()
            self._server = None
            raise Exception(msg)

        self._conn_pool = []
        self._server.newConnection.connect(self._accept)

        with open(self.get_file(), 'w') as stream:
            stream.write(self._server.fullServerName())

    # NOTE: connect() is already taken by Qt
    def open_connection(self, err_hdl=None):
        fp = self.get_file()
        if not os.path.isfile(fp):
            raise Exception('There is no server listening!')

        self._socket = QtNetwork.QLocalSocket()
        self._socket.error.connect(self._sock_error)
        self._socket.connected.connect(self._connected)

        if err_hdl is not None:
            self._socket.error.connect(err_hdl)

        with open(fp, 'r') as stream:
            self._socket.connectToServer(stream.read())

    def send_message(self, msg):
        if self._socket is None:
            self.open_connection()

        if self._socket.state() != QtNetwork.QLocalSocket.ConnectedState:
            self._queue.append(msg)
        else:
            self._socket.write(msg + '\n')

    def close(self, wait=False):
        if self._server is not None:
            self._server.close()
            self._server = None

            self.clean()

        elif self._socket is not None:
            if wait:
                self._socket.waitForBytesWritten(-1)

            self._socket.close()
            self._socket = None

        else:
            raise Exception('IPCComm() is neither listening nor open!')

    def clean(self):
        # NOTE: This disables the server!

        fp = self.get_file()
        if os.path.isfile(fp):
            os.unlink(fp)

    def _accept(self):
        conn = self._server.nextPendingConnection()
        conn.disconnected.connect(functools.partial(self._conn_disc, conn))
        conn.readyRead.connect(functools.partial(self._read_data, conn))

        self._conn_pool.append(conn)

    def _conn_disc(self, conn):
        self._conn_pool.remove(conn)

    def _read_data(self, conn):
        self.messageReceived.emit(conn.readLine())

    def _connected(self):
        for msg in self._queue:
            self._socket.write(msg + '\n')

        self._queue = []

    def _sock_error(self):
        logging.error(self._socket.errorString())


##############
# Public API #
##############

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

#########
# Tools #
#########


def install_scheme_handler():
    if hasattr(sys, 'frozen'):
        my_path = os.path.abspath(sys.executable)
    else:
        my_path = os.path.abspath(__file__)
            
    if sys.platform.startswith('win'):
        settings = QtCore.QSettings('HKEY_CLASSES_ROOT\\fso', QtCore.QSettings.NativeFormat)
        settings.setValue('URLProtocol', '')
        settings.setValue('shell/open/command/@', my_path + ' "%1"')

#         tpl = r"""Windows Registry Editor Version 5.00

# [HKEY_CLASSES_ROOT\fso]
# "URLProtocol"=""

# [HKEY_CLASSES_ROOT\fso\shell]

# [HKEY_CLASSES_ROOT\fso\shell\open]

# [HKEY_CLASSES_ROOT\fso\shell\open\command]
# @="{PATH} \"%1\""
# """
        
#         fd, path = tempfile.mkstemp('.reg')
#         os.write(fd, tpl.replace('{PATH}', my_path.replace('\\', '\\\\')).replace('\n', '\r\n'))
#         os.close(fd)
        
#         try:
#             subprocess.call(['regedit', path])
#         except:
#             logging.exception('Failed!')
        
#         os.unlink(path)
        
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


def scheme_handler(link, app, launcher):
    def handle_error():
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Failed to connect to main process!')
        ipc.clean()
        app.quit()

    if not link.startswith(('fs2://', 'fso://')):
        # NOTE: fs2:// is deprecated, we don't tell anyone about it.
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'I don\'t know how to handle "%s"! I only know fso:// .' % (link))
        app.quit()
        return
    
    link = urlparse.unquote(link).split('/')
    
    if len(link) < 3:
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Not enough arguments!')
        app.quit()
        return
    
    ipc = IPCComm(manager.settings_path)
    if not ipc.server_exists():
        # Launch the program.
        launcher()

        # Wait for the program...
        start = time.time()
        while not ipc.server_exists():
            if time.time() - start > 20:
                # That's too long!
                QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Failed to start server!')
                app.quit()
                return

            time.sleep(0.3)

    try:
        ipc.open_connection(handle_error)
    except:
        logging.exception('Failed to connect to myself!')
        handle_error()
        return

    ipc.send_message(json.dumps(link[2:]))
    ipc.close(True)
    app.quit()
    return


def has_instance():
    return IPCComm(manager.settings_path).server_exists()


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
        manager.main_win.activateWindow()
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

        manager.main_win.activateWindow()

        if mod.mid not in manager.installed.mods:
            install_pkgs(mod.resolve_deps() + pkgs, mod.name)
        else:
            QtGui.QMessageBox.information(manager.main_win, 'fs2mod-py', 'Mod "%s" is already installed!' % (mod.name))
    elif msg[0] == 'settings':
        manager.main_win.activateWindow()

        if len(msg) == 1:
            manager.main_win.tabs.setCurrentIndex(3)
        else:
            mod = get_mod(msg[1])

            if mod.mid not in manager.installed.mods:
                QtGui.QMessageBox.information(manager.main_win, 'fs2mod-py', 'Mod "%s" is not yet installed!' % (mod.name))
            else:
                SettingsWindow(mod)
    else:
        QtGui.QMessageBox.critical(manager.main_win, 'fs2mod-py', 'The action "%s" is unknown!' % (msg[0]))
