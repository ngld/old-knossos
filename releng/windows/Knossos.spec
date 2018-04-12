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
import subprocess
import platform
from PyInstaller.utils.hooks.qt import qt_plugins_binaries

onefile = False
him = ['knossos.parsetab']
debug = os.environ.get('KN_BUILD_DEBUG') == 'yes'
is_x64 = platform.architecture()[0] == '64bit'
rthooks = ['version-rthook.py']

if debug:
    rthooks.append('../../tools/common/debug-rthook.py')

version = subprocess.check_output([sys.executable, '../../setup.py', 'get_version']).decode('utf-8')

if not version:
    print('ERROR: Could not determine version!')
    sys.exit(1)

with open('version-rthook.py', 'w') as stream:
    stream.write('import os;os.environ["KN_VERSION"] = %s' % repr(version))


crt_counter = 0
crt_path = None

for p in (r'C:\Program Files (x86)\Windows Kits\10\Redist\ucrt\DLLs', r'C:\Program Files\Windows Kits\10\Redist\ucrt\DLLs'):
    p = os.path.join(p, 'x64' if is_x64 else 'x86')

    if os.path.isdir(p):
        crt_path = p
        break

pathex = []
if crt_path:
    pathex.append(crt_path)

bins = qt_plugins_binaries('styles', namespace='PyQt5')

a = Analysis(['../../knossos/__main__.py'],
            pathex=pathex,
            hiddenimports=him,
            binaries=bins,
            hookspath=[],
            runtime_hooks=rthooks,
            datas=[
                ('../../knossos/data/hlp.ico', 'data'),
                ('../../knossos/data/resources.rcc', 'data')
            ])

# Exclude everything we don't need.
idx = []

for i, item in enumerate(a.binaries):
    fn = item[0].lower()
    if fn.startswith(('ole', 'user32')):
        idx.append(i)

for i in reversed(idx):
    del a.binaries[i]

idx = []
for i, item in enumerate(a.pure):
    if item[0].startswith(('pydoc', 'pycparser')):
        idx.append(i)

for i in reversed(idx):
    del a.pure[i]

pyz = PYZ(a.pure)

arch_prefix = ''
if is_x64:
    arch_prefix = 'x64/'

a.datas += [('7z.exe', 'support/7z.exe', 'BINARY'),
            ('7z.dll', 'support/7z.dll', 'BINARY'),
            ('SDL2.dll', 'support/%sSDL2.dll' % arch_prefix, 'BINARY'),
            ('OpenAL32.dll', 'support/%sOpenAL32.dll'% arch_prefix, 'BINARY'),
            ('taskbar.tlb', 'support/taskbar.tlb', 'BINARY')]


if onefile:
    exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
              exclude_binaries=False,
              name='Knossos.exe',
              icon='../../knossos/data/hlp.ico',
              debug=False,
              strip=None,
              upx=False,
              console=debug)
else:
    exe = EXE(pyz,
              a.scripts,
              exclude_binaries=True,
              name='Knossos.exe',
              icon='../../knossos/data/hlp.ico',
              debug=False,
              strip=None,
              upx=not debug,
              console=debug)

    if crt_path:
        for item in a.binaries:
            if item[0].lower().startswith('api-ms-') and not item[1].startswith(crt_path):
                item[1] = os.path.join(crt_path, item[0])
                crt_counter += 1

    if crt_counter > 0:
        logging.info('%d CRT DLLs replaced with versions from the 7 SDK.')

    coll = COLLECT(exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   strip=None,
                   upx=False,  # upx breaks Qt somehow
                   name='Knossos')
