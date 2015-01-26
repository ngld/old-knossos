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

import sys
import os.path
from PyInstaller.hooks.hookutils import eval_statement, logger, misc, is_win

hiddenimports = []
_qt_dir = None


def qt_plugin_binaries(plug_type):
    global _qt_dir

    if _qt_dir is None:
        dirs = eval_statement(
            'from PySide.QtCore import QCoreApplication;' +
            'app = QCoreApplication([]);' +
            'print map(unicode, app.libraryPaths())'
        )

        if not dirs:
            logger.error('Can\'t find PySide plugin directories.')
            return

        for path in dirs:
            if os.path.isdir(path):
                _qt_dir = str(path)
                break

        if _qt_dir is None:
            logger.error('PySide didn\'t provide any existing plugin directory.')
            return
        else:
            # Make sure PyInstaller finds all dlls.
            sys.path.append(os.path.dirname(_qt_dir))

    dlls = misc.dlls_in_dir(os.path.join(_qt_dir, plug_type))
    if is_win:
        dlls = [p for p in dlls if not p.endswith('d4.dll')]

    for path in dlls:
        yield (os.path.join('plugins', plug_type, os.path.basename(path)), path, 'BINARY')


def hook(mod):
    mod.pyinstaller_binaries.extend(qt_plugin_binaries('accessible'))
    mod.pyinstaller_binaries.extend(qt_plugin_binaries('iconengines'))
    mod.pyinstaller_binaries.extend(qt_plugin_binaries('imageformats'))
    mod.pyinstaller_binaries.extend(qt_plugin_binaries('inputmethods'))
    mod.pyinstaller_binaries.extend(qt_plugin_binaries('graphicssystems'))
    return mod
