## Copyright 2017 Knossos authors, see NOTICE file
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

import os
import uuid
import logging
import functools

from . import uhf
uhf(__name__)

from .qt import QtCore, QtNetwork


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

        name = 'knossos-' + str(uuid.uuid4())
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
            addr = stream.read()

        self._socket.connectToServer(addr)

    def send_message(self, msg):
        if self._socket is None:
            self.open_connection()

        if self._socket.state() != QtNetwork.QLocalSocket.ConnectedState:
            self._queue.append(msg)
        else:
            self._socket.write((msg + '\n').encode('utf8'))

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
            self._socket.write((msg + '\n').encode('utf8'))

        self._queue = []

    def _sock_error(self):
        logging.warning(self._socket.errorString())
