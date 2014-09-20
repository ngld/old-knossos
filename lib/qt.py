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

import os
import logging

default_variant = 'PySide'

variant = os.environ.get('QT_API', default_variant)
if variant not in ('PySide', 'PyQt4', 'headless'):
    logging.warning('Unknown QT_API "%s"! Using default...', variant)
    variant = default_variant

if variant == 'PySide':
    try:
        from PySide import QtCore, QtGui, QtNetwork, QtWebKit
    except ImportError:
        # Fallback to PyQt4
        variant = 'PyQt4'

if variant == 'PyQt4':
    try:
        import sip
        api2_classes = [
            'QData', 'QDateTime', 'QString', 'QTextStream',
            'QTime', 'QUrl', 'QVariant',
        ]

        for cl in api2_classes:
            sip.setapi(cl, 2)

        from PyQt4 import QtCore, QtGui, QtNetwork, QtWebKit
        
        QtCore.Signal = QtCore.pyqtSignal
        QtCore.Slot = QtCore.pyqtSlot
        QtCore.QString = str
        
    except ImportError:
        # Fallback to headless
        variant = 'headless'

if variant == 'headless':
    if os.environ.get('QT_API') != 'headless':
        logging.warning('Falling back to headless mode. This WILL fail if you want to use the mod manager!')

    # This is just a dummy implementation of the QtCore.Signal() system. Nothing else is provided by this variant.
    import threading
    import time

    _main_loop = None

    class _App(object):
        _running = True
        _queue = None
        _queue_lock = None

        def __init__(self, args):
            global _main_loop

            _main_loop = self
            self._queue = []
            self._queue_lock = threading.Lock()

        def schedule(self, cb, args):
            with self._queue_lock:
                self._queue.append((cb, args))

        def quit(self):
            self._running = False

        def exit(self, code=0):
            self._running = False

        def exec_(self):
            while self._running:
                time.sleep(0.3)

                with self._queue_lock:
                    q = self._queue
                    self._queue = []

                for cb, args in q:
                    cb(*args)

    class _Signal(object):
        _listeners = None
        _lock = None

        def __init__(self, *argtypes):
            # NOTE: Since this is just a dummy implementation, I won't check the argtypes...
            self._listeners = []
            self._lock = threading.Lock()

        def connect(self, cb):
            with self._lock:
                self._listeners.append(cb)

        def disconnect(self, cb):
            with self._lock:
                self._listeners.remove(cb)

        def emit(self, *args):
            global _main_loop

            with self._lock:
                for cb in self._listeners:
                    _main_loop.schedule(cb, args)

    class QtCore(object):
        QObject = object
        QCoreApplication = _App
        Signal = _Signal

    class QtGui(object):
        QApplication = _App
        QDialog = object

    QtWebKit = None

logging.debug('Using Qt API %s.', variant)
__all__ = ['QtCore', 'QtGui', 'QtNetwork', 'QtWebKit', 'variant']
