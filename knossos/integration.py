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
import logging
import ctypes
import six

from . import center, clibs, qt

if six.PY2:
    ctypes.pythonapi.PyCObject_AsVoidPtr.argtypes = [ctypes.py_object]
    ctypes.pythonapi.PyCObject_AsVoidPtr.restype = ctypes.c_void_p
else:
    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p


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
        pass


class UnityIntegration(Integration):
    launcher = None

    def __init__(self, Unity):
        self.launcher = Unity.LauncherEntry.get_for_desktop_id('Knossos.desktop')

    def show_progress(self, value):
        self.launcher.set_property('progress_visible', True)
        self.set_progress(value)

    def set_progress(self, value):
        self.launcher.set_property('progress', value)

    def hide_progress(self):
        self.launcher.set_property('progress_visible', False)

    def annoy_user(self, activate=True):
        self.launcher.set_property('urgent', activate)


class WindowsIntegration(Integration):
    TBPF_NOPROGRESS = 0x0
    TBPF_INDETERMINATE = 0x1
    TBPF_NORMAL = 0x2
    TBPF_ERROR = 0x4
    TBPF_PAUSED = 0x8

    taskbar = None
    _hwnd = None
    _win = None

    def __init__(self, taskbar):
        self.taskbar = taskbar
        taskbar.HrInit()

    def wid(self):
        win = center.main_win.win
        if win != self._win:
            if six.PY2:
                self._hwnd = ctypes.pythonapi.PyCObject_AsVoidPtr(win.winId())
            else:
                self._hwnd = ctypes.pythonapi.PyCapsule_GetPointer(win.winId(), None)
            self._win = win
        
        return self._hwnd

    def show_progress(self, value):
        self.taskbar.SetProgressState(self.wid(), self.TBPF_NORMAL)
        self.set_progress(value)

    def set_progress(self, value):
        self.taskbar.SetProgressValue(self.wid(), int(value * 100), 100)

    def hide_progress(self):
        self.taskbar.SetProgressState(self.wid(), self.TBPF_NOPROGRESS)

    def annoy_user(self, activate=True):
        pass

current = None


def init():
    global current

    if sys.platform.startswith('win'):
        try:
            import comtypes.client as cc
            cc.GetModule('taskbar.tlb')

            import comtypes.gen.TaskbarLib as tbl
            taskbar = cc.CreateObject('{56FDF344-FD6D-11d0-958A-006097C9A090}', interface=tbl.ITaskbarList3)
        except:
            logging.exception('Failed to load ITaskbarList3! Disabling Windows integration.')
        else:
            logging.info('Activating Windows integration...')
            current = WindowsIntegration(taskbar)
            return
    elif sys.platform.startswith('linux'):
        # TODO: Do we really have to initialize GTK?

        clibs.init_gtk()
        theme = clibs.get_gtk_theme()
        if theme == 'Ambiance':
            center.main_win.win.setStyleSheet(qt.load_styles(':/ui/themes/Ambiance/style.css'))
            center.main_win.win.setContentsMargins(-9, -9, -9, -9)
            center.main_win.win.verticalLayout.setSpacing(0)

        try:
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
