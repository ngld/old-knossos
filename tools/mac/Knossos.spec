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
import os
import logging
import ctypes.util


def which(cmd):
    path = os.environ.get('PATH', os.defpath)
    if not path:
        return None
    path = path.split(os.pathsep)
    
    seen = set()
    for dir in path:
        normdir = os.path.normcase(dir)
        if not normdir in seen:
            seen.add(normdir)
            name = os.path.join(dir, cmd)
            if (os.path.exists(name) and os.access(name, os.F_OK | os.X_OK)
                    and not os.path.isdir(name)):
                return name

    return None

debug = os.environ.get('KN_BUILD_DEBUG') == 'yes'

# Make sure all paths that end up in the compiled executable are relative.
pd = config['PYZ_dependencies']
for i, item in enumerate(pd):
    if '/Users/' in item[1]:
        pd[i] = (item[0], os.path.relpath(item[1]), item[2])

# Fix a bug in PyInstaller's current hook-sysconfig.py
sys.prefix = os.path.realpath(sys.prefix)

# Look for our dependencies
p7z_path = which('7z')
if not p7z_path:
    logging.error('I can\'t find 7z! If you have Homebrew, just run "brew install p7zip".')
    sys.exit(1)

with open(p7z_path, 'r') as stream:
    if stream.read(2) == '#!':
        p7z_path = stream.readlines()[1].split('"')[1]


sdl2_path = ctypes.util.find_library('SDL2')
sdl_path = ctypes.util.find_library('SDL')
if not sdl2_path and not sdl_path:
    logging.error('I can\'t find SDL! If you have Homebrew, just run "brew install sdl2".')
    sys.exit(1)

# Use the PySide hooks from the windows build. They work for Mac OS, too.
rthooks = ['../common/PySide-rthook.py']
if debug:
    rthooks.append('../common/debug-rthook.py')

a = Analysis(['../../knossos/__main__.py'],
             pathex=['../..'],
             hiddenimports=[],
             hookspath=['../common'],
             runtime_hooks=rthooks)

# Exclude everything we don't need.
idx = []
for i, item in enumerate(a.binaries):
    if item[0].startswith('PySide.') and item[0] not in ('PySide.QtCore', 'PySide.QtGui', 'PySide.QtNetwork', 'PySide.QtWebKit'):
        idx.append(i)
    elif item[0].startswith('Qt') and item[0] not in ('QtCore', 'QtGui', 'QtNetwork', 'QtWebKit'):
        idx.append(i)
    elif item[0].startswith('plugins') and not item[0].endswith(('libqjpeg.dylib', 'libqgif.dylib')):
        idx.append(i)

for i in reversed(idx):
    del a.binaries[i]

idx = []
for i, item in enumerate(a.pure):
    if item[0].startswith('pydoc'):
        idx.append(i)

for i in reversed(idx):
    del a.pure[i]

pyz = PYZ(a.pure)

a.datas += [('7z', p7z_path, 'DATA'),
            ('version', 'version', 'DATA'),
            ('data/hlp.ico', '../../knossos/data/hlp.ico', 'DATA'),
            ('data/resources.rcc', '../../knossos/data/resources.rcc', 'DATA')]

if sdl2_path:
    a.datas += [('libSDL2.dylib', sdl2_path, 'BINARY')]
else:
    a.datas += [('libSDL.dylib', sdl_path, 'BINARY')]

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Knossos',
          debug=False,
          strip=None,
          upx=False,
          console=debug)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=False,
               name='Knossos')

if not debug:
    app = BUNDLE(coll,
                 name='Knossos.app',
                 icon='../../knossos/data/hlp.icns')
