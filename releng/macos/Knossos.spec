# -*- mode: python -*-
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
import logging
import subprocess
import ctypes.util
import PyQt5
from shutil import which, copytree
from PyInstaller.utils.hooks.qt import qt_plugins_binaries

him = ['knossos.parsetab']
debug = os.environ.get('KN_BUILD_DEBUG') == 'yes'

rthooks = ['version-rthook.py']
if debug:
    rthooks.append('../../tools/common/debug-rthook.py')

# Fix a bug in PyInstaller's current hook-sysconfig.py
sys.prefix = os.path.realpath(sys.prefix)

# Look for our dependencies
p7zip_path = which('7z')
if not p7zip_path:
    logging.error('I can\'t find 7z! If you have Homebrew, just run "brew install p7zip".')
    sys.exit(1)

with open(p7zip_path, 'r') as stream:
    if stream.read(2) == '#!':
        p7zip_path = stream.readlines()[1].split('"')[1]

if os.path.islink(p7zip_path):
    p7zip_path = os.readlink(p7zip_path)

p7zip_lib = os.path.join(os.path.dirname(p7zip_path), '7z.so')
if not os.path.isfile(p7zip_lib):
    logging.error('7z.so not found! Please make sure that it\'s near the 7z binary!')
    sys.exit(1)

sdl2_path = ctypes.util.find_library('SDL2')
if not sdl2_path:
    logging.error('I can\'t find SDL! Please go to https://libsdl.org/download-2.0.php, download the .dmg file and ' +
        'install it according to the contained README.')
    sys.exit(1)

if not os.path.dirname(sdl2_path).endswith('.framework'):
    logging.error('Found SDL2 in %s but I need a framework! Please go to https://libsdl.org/download-2.0.php, ' % sdl2_path +
        'download the .dmg file and install it according to the contained README.')
    sys.exit(1)

version = subprocess.check_output([sys.executable, '../../setup.py', 'get_version']).decode('utf-8')

if not version:
    print('ERROR: Could not determine version!')
    sys.exit(1)

with open('version-rthook.py', 'w') as stream:
    stream.write('import os;os.environ["KN_VERSION"] = %s' % repr(version))


qt_path = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt', 'lib')
resources_dir = os.path.join(qt_path, 'QtWebEngineCore.framework', 'Resources')
a = Analysis(['../../knossos/__main__.py'],
            pathex=[],
            hiddenimports=him,
            hookspath=[],
            runtime_hooks=rthooks,
            binaries=[
                # Add QtWebEngine stuff because PyInstaller's hook doesn't do anything without qmake (which PyQt5 doesn't include).
                (os.path.join(qt_path, 'QtWebEngineCore.framework', 'Helpers', 'QtWebEngineProcess.app',
                    'Contents', 'MacOS', 'QtWebEngineProcess'),
                os.path.join('QtWebEngineProcess.app', 'Contents', 'MacOS'))
            ] + qt_plugins_binaries('styles', namespace='PyQt5'),
            datas=[
                (p7zip_path, '.'),
                (p7zip_lib, '.'),
                ('../../knossos/data/resources.rcc', 'data'),

                # Add QtWebEngine stuff because PyInstaller's hook doesn't do anything without qmake (which PyQt5 doesn't include).
                (os.path.join(resources_dir, 'icudtl.dat'), '.'),
                (os.path.join(resources_dir, 'qtwebengine_resources.pak'), '.'),
                (os.path.join(resources_dir, 'qtwebengine_resources_100p.pak'), '.'),
                (os.path.join(resources_dir, 'qtwebengine_resources_200p.pak'), '.'),

                # The distributed Info.plist has LSUIElement set to true, which prevents the
                # icon from appearing in the dock.
                (os.path.join(qt_path, 'QtWebEngineCore.framework', 'Helpers', 'QtWebEngineProcess.app', 'Contents', 'Info.plist'),
                    os.path.join('QtWebEngineProcess.app', 'Contents'))
])

# Exclude everything we don't need.
idx = []
for i, item in enumerate(a.pure):
    if item[0].startswith(('pydoc', 'pycparser')):
        idx.append(i)

for i in reversed(idx):
    del a.pure[i]

pyz = PYZ(a.pure)

# Build the binary
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Knossos',
          debug=False,
          strip=None,
          upx=False,
          console=debug)

# Build the .app folder
app = BUNDLE(exe,
            a.binaries,
            a.zipfiles,
            a.datas,
            bundle_identifier='org.qt-project.Qt.QtWebEngineCore',  # see PyInstaller.hooks.hook-PyQt5.QtWebEngineWidgets
            name='Knossos.app',
            icon='../../knossos/data/hlp.icns',
            info_plist={
              'CFBundleShortVersionString': version
            })

copytree(os.path.dirname(sdl2_path), os.path.join(DISTPATH, 'Knossos.app/Contents/Frameworks/SDL2.framework'))
