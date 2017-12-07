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

import sys
import os
import logging


os.environ['DBUS_FATAL_WARNINGS'] = '0'

try:
    from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork

    try:
        from PyQt5 import QtWebChannel, QtWebEngineWidgets

        try:
            from PyQt5 import QtWebSockets
        except ImportError:
            QtWebSockets = None
    except ImportError:
        from PyQt5 import QtWebKit, QtWebKitWidgets

        QtWebChannel = None

        class QtWebEngineWidgets(object):
            QWebEngineView = QtWebKitWidgets.QWebView

    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot
    QtCore.QString = str

    # Success!
    variant = 'PyQt5'

except ImportError:
    logging.exception('I was unable to load Qt! Tried PyQt5.')
    sys.exit(1)


class SignalContainer(QtCore.QObject):
    signal = QtCore.Signal(list)


def read_file(path, decode=True):
    fd = QtCore.QFile(path)
    if not fd.open(QtCore.QIODevice.ReadOnly):
        return None

    data = fd.readAll().data()
    fd.close()

    if decode:
        return data.decode('utf-8')
    else:
        return data


def load_styles(*names):
    data = ''
    for name in names:
        if ':/' in name:
            sheet = read_file(name)
        else:
            with open(name, 'r') as stream:
                sheet = stream.read()

        data += sheet.replace('url(./', 'url(' + os.path.dirname(name) + '/')

    return data


# This wrapper makes sure that the wrapped function is always run in the QT main thread.
def run_in_qt(func):
    cont = SignalContainer()

    def dispatcher(*args):
        cont.signal.emit(list(args))

    def listener(params):
        func(*params)

    cont.signal.connect(listener)

    return dispatcher


__all__ = [
    'QtCore', 'QtGui', 'QtWidgets', 'QtNetwork', 'QtWebChannel', 'QtWebEngineWidgets', 'QtWebKit', 'QtWebSockets',
    'read_file', 'load_styles', 'run_in_qt'
]
