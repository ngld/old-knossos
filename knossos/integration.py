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
import logging

from . import uhf
uhf(__name__)

from . import center, qt


tr = qt.QtCore.QCoreApplication.translate


class Integration(object):

    def shutdown(self):
        pass

    def show_progress(self, value):
        pass

    def set_progress(self, value):
        pass

    def hide_progress(self):
        pass

    def annoy_user(self, activate=True):
        if center.main_win and activate:
            center.app.alert(center.main_win, 3000)

    def set_busy(self):
        self.show_progress(0)


class UnityIntegration(Integration):

    def __init__(self, Unity):
        try:
            self.launcher = Unity.LauncherEntry.get_for_desktop_id('knossos.desktop')
        except Exception:
            self.launcher = None
            logging.exception('Failed to initialize LauncherEntry for Unity.')

    def show_progress(self, value):
        if self.launcher:
            try:
                self.launcher.set_property('progress_visible', True)
                self.set_progress(value)
            except Exception:
                logging.exception('Setting progress_visible for Unity failed!')

    def set_progress(self, value):
        if self.launcher:
            try:
                self.launcher.set_property('progress', value)
            except Exception:
                logging.exception('Setting progress for Unity failed!')

    def hide_progress(self):
        if self.launcher:
            try:
                self.launcher.set_property('progress_visible', False)
            except Exception:
                logging.exception('Setting progress_visible for Unity failed!')

    def annoy_user(self, activate=True):
        super(UnityIntegration, self).annoy_user(activate)

        if self.launcher:
            try:
                self.launcher.set_property('urgent', activate)
            except Exception:
                logging.exception('Setting urgent for Unity failed!')


class WindowsIntegration(Integration):
    _win = None
    _busy = False

    def __init__(self):
        from PyQt5 import QtWinExtras

        self._button = QtWinExtras.QWinTaskbarButton()
        self._button.setWindow(center.main_win.win.windowHandle())
        self._progress = self._button.progress()

    def show_progress(self, value):
        self.set_progress(value)
        self._progress.show()

    def set_progress(self, value):
        if self._busy:
            self._busy = False
            self._progress.setRange(0, 100)

        self._progress.setValue(int(value * 100))

    def hide_progress(self):
        self._progress.hide()

    def set_busy(self):
        if self._busy:
            self._progress.show()
            return

        self._busy = True
        self._progress.setRange(0, 0)
        self._progress.setValue(0)
        self._progress.show()


current = None


def init():
    global current

    if sys.platform == 'win32':
        try:
            logging.info('Activating Windows integration...')
            current = WindowsIntegration()
            return
        except Exception:
            logging.exception('Failed to activate the Windows integration.')

    elif sys.platform.startswith('linux'):
        try:
            import gi
            try:
                if hasattr(gi, 'require_version'):
                    gi.require_version('Unity', '6.0')
            except Exception:
                logging.warning('Failed to specify Unity version. Most likely Unity is not available.')

            from gi.repository import Unity
        except ImportError:
            # Can't find Unity.
            pass
        else:
            logging.info('Activating Unity integration...')
            current = UnityIntegration(Unity)
            return

    logging.info('No desktop integration active.')
    current = Integration()
