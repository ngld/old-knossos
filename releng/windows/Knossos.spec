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
import PyQt5

onefile = False
him = ['knossos.parsetab']
debug = os.environ.get('KN_BUILD_DEBUG') == 'yes'
is_x64 = platform.architecture()[0] == '64bit'


# Build the TaskbarLib module.
try:
    import comtypes.client as cc
    cc.GetModule('support/taskbar.tlb')

    import comtypes.gen as cg
    gen_path = os.path.dirname(cg.__file__)

    for fname in os.listdir(gen_path):
        if not fname.startswith('__'):
            him.append('comtypes.gen.' + fname.split('.')[0])
except:
    import logging
    logging.exception('Failed to generate comtypes.gen.TaskbarLib!')

rthooks = ['version-rthook.py']
if debug:
    rthooks.append('../../tools/common/debug-rthook.py')

qt_path = os.path.dirname(PyQt5.__file__)
qt_bin = os.path.join(qt_path, 'qt', 'bin')

version = subprocess.check_output([sys.executable, '../../setup.py', 'get_version']).decode('utf-8')

if not version:
    print('ERROR: Could not determine version!')
    sys.exit(1)

with open('version-rthook.py', 'w') as stream:
    stream.write('import os;os.environ["KN_VERSION"] = %s' % repr(version))

a = Analysis(['../../knossos/__main__.py'],
            pathex=['../..', 'py-env/lib/site-packages/PyQt5/qt/bin'],
            hiddenimports=him,
            hookspath=[],
            runtime_hooks=rthooks,
            datas=[
                ('../../knossos/data/hlp.ico', 'data'),
                ('../../knossos/data/resources.rcc', 'data'),
                ('../../knossos/parser.out', 'knossos'),
                (os.path.join(qt_path, 'qt', 'resources'), '.')
            ])

# Exclude everything we don't need.
idx = []
crt_counter = 0
crt_path = None

for p in (r'C:\Program Files (x86)\Windows Kits\7\Redist\ucrt\DLLs', r'C:\Program Files\Windows Kits\7\Redist\ucrt\DLLs'):
    p = os.path.join(p, 'x64' if is_x64 else 'x86')

    if os.path.isdir(p):
        crt_path = p
        break


for i, item in enumerate(a.binaries):
    fn = item[0].lower()
    if fn.startswith(('ole', 'user32')):
        idx.append(i)

    if crt_path and fn.startswith('api-ms-'):
        item[1] = os.path.join(crt_path, fn)
        crt_counter += 1

if crt_counter > 0:
    logging.info('%d CRT DLLs replaced with versions from the 7 SDK.')


for i in reversed(idx):
    del a.binaries[i]

idx = []
for i, item in enumerate(a.pure):
    if item[0].startswith(('pydoc', 'pycparser')):
        idx.append(i)
    elif item[0] == 'comtypes.client._code_cache':
        a.pure[i] = (item[0], './comtypes_code_cache.py', item[2])

for i in reversed(idx):
    del a.pure[i]

pyz = PYZ(a.pure)

a.datas += [('7z.exe', 'support/7z.exe', 'BINARY'),
            ('7z.dll', 'support/7z.dll', 'BINARY'),
            ('SDL2.dll', 'support/SDL2.dll', 'BINARY'),
            ('openal.dll', 'support/openal.dll', 'BINARY'),
            ('taskbar.tlb', 'support/taskbar.tlb', 'BINARY')]

for name in ('QtWebEngineProcess.exe', 'libEGL.dll', 'libGLESv2.dll'):
    a.datas.append((name, os.path.join(qt_bin, name), 'BINARY'))


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

    coll = COLLECT(exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   strip=None,
                   upx=False,  # upx breaks Qt somehow
                   name='Knossos')
