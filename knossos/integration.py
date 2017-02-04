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
import ctypes
import shlex
import six

from . import center, qt, launcher

if qt.variant == 'PySide':
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

    def install_scheme_handler(self):
        pass


class LinuxIntegration(Integration):

    def install_scheme_handler(self):
        my_cmd = launcher.get_cmd()

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
        desktop_file = applications_path + 'knossos.desktop'
        mime_types_file = applications_path + 'mimeapps.list'
        my_path = ' '.join([shlex.quote(p) for p in my_cmd])

        if os.path.isfile(desktop_file) or os.path.isfile('/usr/share/applications/knossos.desktop'):
            return True

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

        return True


class UnityIntegration(LinuxIntegration):
    launcher = None

    def __init__(self, Unity):
        self.launcher = Unity.LauncherEntry.get_for_desktop_id('knossos.desktop')

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
            if qt.variant == 'PySide':
                if six.PY2:
                    self._hwnd = ctypes.pythonapi.PyCObject_AsVoidPtr(win.winId())
                else:
                    self._hwnd = ctypes.pythonapi.PyCapsule_GetPointer(win.winId(), None)
            else:
                self._hwnd = win.winId()
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

    def install_scheme_handler(self):
        my_cmd = launcher.get_cmd()

        settings = qt.QtCore.QSettings('HKEY_CLASSES_ROOT\\fso', qt.QtCore.QSettings.NativeFormat)
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
        settings = qt.QtCore.QSettings('HKEY_CLASSES_ROOT\\fso', qt.QtCore.QSettings.NativeFormat)
        settings.setFallbacksEnabled(False)

        return settings.value('shell/open/command/Default') == my_path


current = None


def init():
    global current

    if sys.platform.startswith('win'):
        try:
            import comtypes.client as cc

            tbl = cc.GetModule('taskbar.tlb')
            taskbar = cc.CreateObject('{56FDF344-FD6D-11d0-958A-006097C9A090}', interface=tbl.ITaskbarList3)
        except:
            logging.exception('Failed to load ITaskbarList3! Disabling Windows integration.')
        else:
            logging.info('Activating Windows integration...')
            current = WindowsIntegration(taskbar)
            return
    elif sys.platform.startswith('linux'):
        try:
            from gi.repository import Unity
        except ImportError:
            # Can't find Unity.
            pass
        else:
            logging.info('Activating Unity integration...')
            current = UnityIntegration(Unity)
            return

        logging.info('Activating generic Linux integration...')
        current = LinuxIntegration()
        return

    logging.warning('No desktop integration active.')
    current = Integration()
