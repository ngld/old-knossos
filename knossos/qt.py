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

default_variant = 'auto'
QtCore = None

variant = os.environ.get('QT_API', default_variant)
if variant not in ('PyQt5', 'headless', default_variant):
    logging.warning('Unknown QT_API "%s"! Using default...', variant)
    variant = default_variant

if variant != 'headless':
    # Make sure we initialize Xlib before we load Qt.
    from . import clibs

if variant in ('PyQt5', 'auto'):
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork

        try:
            from PyQt5 import QtWebChannel, QtWebEngineWidgets
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

if variant == 'headless':
    # This is just a dummy implementation of the QtCore.Signal() system. Nothing else is provided by this variant.
    import threading
    import time

    _main_loop = None

    class _App(object):
        _running = True
        _queue = None
        _queue_lock = None
        _timers = None

        def __init__(self, args):
            global _main_loop

            _main_loop = self
            self._queue = []
            self._queue_lock = threading.Lock()
            self._timers = []

        def reset(self):
            self._queue = []
            self._timers = []
            self._running = True

        def schedule(self, cb, args):
            with self._queue_lock:
                self._queue.append((cb, args))

        def set_timer(self, cb, timeout):
            with self._queue_lock:
                self._timers.append((cb, time.time() + timeout))

        def quit(self):
            self._running = False

        def exit(self, code=0):
            self._running = False

        def exec_(self):
            while self._running:
                time.sleep(0.3)
                ct = time.time()

                with self._queue_lock:
                    q = self._queue
                    self._queue = []

                    for i in range(len(self._timers) - 1, -1, -1):
                        if self._timers[i][1] < ct:
                            q.append((self._timers[i][0], []))
                            del self._timers[i]

                for cb, args in q:
                    cb(*args)

    class _Signal(object):
        _listeners = None
        _lock = None
        _active = False

        def __init__(self, *argtypes):
            # NOTE: Since this is just a dummy implementation, I won't check the argtypes...
            pass

        def _init(self):
            inst = _Signal()
            inst._listeners = []
            inst._lock = threading.Lock()
            return inst

        def connect(self, cb):
            if self._lock is None:
                raise Exception('QtCore.Signal() was not initialized correctly!')

            with self._lock:
                self._listeners.append(cb)

        def disconnect(self, cb):
            if self._lock is None:
                raise Exception('QtCore.Signal() was not initialized correctly!')

            with self._lock:
                self._listeners.remove(cb)

        def emit(self, *args):
            global _main_loop

            if self._lock is None:
                raise Exception('QtCore.Signal() was not initialized correctly!')

            with self._lock:
                for cb in self._listeners:
                    _main_loop.schedule(cb, args)

    class _QObject(object):

        def __init__(self):
            super(_QObject, self).__init__()

            # Init this class's signals for every instance.
            done = []
            bases = list(self.__class__.__bases__)
            bases.append(self.__class__)
            for base in bases:
                for name in base.__dict__:
                    if name not in done:
                        val = getattr(self, name)
                        done.append(name)

                        if isinstance(val, _Signal):
                            setattr(self, name, val._init())

    class _QTimer(object):

        @staticmethod
        def singleShot(timeout, cb):
            global _main_loop
            _main_loop.set_timer(cb, timeout / 1000.)

    class QtCore(object):
        QObject = _QObject
        QCoreApplication = _App
        Signal = _Signal
        QTimer = _QTimer
        QByteArray = None

    class QtGui(object):
        QDialog = _QObject

    class QtWidgets(object):
        QApplication = _App

    QtNetwork = None
    QtWebChannel = None
    QtWebEngineWidgets = None


def read_file(path):
    fd = QtCore.QFile(path)
    fd.open(QtCore.QIODevice.ReadOnly)
    data = str(fd.readAll())
    fd.close()

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


__all__ = ['QtCore', 'QtGui', 'QtWidgets', 'QtNetwork', 'QtWebChannel', 'QtWebEngineWidgets', 'QtWebKit', 'variant', 'read_file', 'load_styles']
