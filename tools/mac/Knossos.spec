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
import re
import shutil


def which(cmd):
    path = os.environ.get('PATH', os.defpath)
    if not path:
        return None

    path = path.split(os.pathsep)

    seen = set()
    for dir in path:
        normdir = os.path.normcase(dir)
        if normdir not in seen:
            seen.add(normdir)
            name = os.path.join(dir, cmd)
            if (os.path.exists(name) and os.access(name, os.F_OK | os.X_OK) and
                    not os.path.isdir(name)):
                return name

    return None


debug = os.environ.get('KN_BUILD_DEBUG') == 'yes'

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
if not sdl2_path:
    logging.error('I can\'t find SDL! Please go to https://libsdl.org/download-2.0.php, download the .dmg file and ' +
        'install it according to the contained README.')
    sys.exit(1)

if not os.path.dirname(sdl2_path).endswith('.framework'):
    logging.error('Found SDL2 in %s but I need a framework! Please go to https://libsdl.org/download-2.0.php, ' +
        'download the .dmg file and install it according to the contained README.' % sdl2_path)
    sys.exit(1)

# Persist the debug setting
rthooks = []
if debug:
    rthooks.append('../common/debug-rthook.py')

# Read the version number
with open('../../knossos/center.py') as stream:
    match = re.search(r"VERSION = '([^']+)'", stream.read())

if not match:
    print('ERROR: Could not determine version!')
    sys.exit(1)

version = match.group(1)
if '-dev' in version:
    # Append the current commit to the version number
    if not os.path.exists('../../.git'):
        print('\nWARNING: No .git directory found while building a devbuild!\n')
    else:
        with open('../../.git/HEAD') as stream:
            ref = stream.read().strip().split(':')
            assert ref[0] == 'ref'

        with open('../../.git/' + ref[1].strip()) as stream:
            version += '+' + stream.read()[:7]

with open('version', 'w') as stream:
    stream.write(version)

# Generate a list of dependencies
a = Analysis(['../../knossos/__main__.py'],
             pathex=['../..'],
             hiddenimports=[],
             hookspath=['../common'],
             runtime_hooks=rthooks)

idx = []
for i, item in enumerate(a.pure):
    if item[0].startswith('pydoc'):
        idx.append(i)

for i in reversed(idx):
    del a.pure[i]

# Build an archive of all pure python files
pyz = PYZ(a.pure)

a.datas += [('7z', p7z_path, 'DATA'),
            ('version', 'version', 'DATA'),
            ('data/hlp.ico', '../../knossos/data/hlp.ico', 'DATA'),
            ('data/resources.rcc', '../../knossos/data/resources.rcc', 'DATA')]

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
             name='Knossos.app',
             icon='../../knossos/data/hlp.icns',
             info_plist={
                'CFBundleShortVersionString': version
             })

shutil.copytree(os.path.dirname(sdl2_path), os.path.join(DISTPATH, 'Knossos.app/Contents/Frameworks/SDL2.framework'))
