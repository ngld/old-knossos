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

import os.path

onefile = False
him = []
debug = os.environ.get('KN_BUILD_DEBUG') == 'yes'

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


rthooks = []  # ['../common/PySide-rthook.py']
if debug:
    rthooks.append('../common/debug-rthook.py')

a = Analysis(['../../knossos/__main__.py'],
             pathex=['../..'],
             hiddenimports=him,
             hookspath=['../common'],
             runtime_hooks=rthooks)

# Exclude everything we don't need.
idx = []
for i, item in enumerate(a.binaries):
    if item[0].startswith('PySide.') and item[0] not in ('PySide.QtCore', 'PySide.QtGui', 'PySide.QtNetwork', 'PySide.QtWebKit'):
        idx.append(i)
    elif item[0].lower().startswith('qt') and item[0].lower() not in ('qtcore4.dll', 'qtgui4.dll', 'qtnetwork4.dll', 'qtwebkit4.dll'):
        idx.append(i)
    elif item[0].startswith('plugins') and not item[0].endswith(('qjpeg4.dll', 'qgif4.dll')):
        idx.append(i)
    elif item[0].startswith('ole') or item[0].startswith('user32'):
        idx.append(i)

for i in reversed(idx):
    del a.binaries[i]

idx = []
for i, item in enumerate(a.pure):
    if item[0].startswith(('pydoc', 'pycparser')):
        idx.append(i)
    elif item[0] == 'comtypes.client._code_cache':
        a.pure[i] = (item[0], './comtypes_code_cache.pyo', item[2])

for i in reversed(idx):
    del a.pure[i]

pyz = PYZ(a.pure)

a.datas += [('7z.exe', 'support/7z.exe', 'BINARY'),
            ('7z.dll', 'support/7z.dll', 'BINARY'),
            ('version', 'version', 'DATA'),
            ('data/hlp.ico', '../../knossos/data/hlp.ico', 'DATA'),
            ('data/resources.rcc', '../../knossos/data/resources.rcc', 'DATA'),
            ('SDL2.dll', 'support/SDL2.dll', 'BINARY'),
            ('openal.dll', 'support/openal.dll', 'BINARY'),
            ('taskbar.tlb', 'support/taskbar.tlb', 'BINARY')]


if onefile:
    exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
              exclude_binaries=False,
              name='Knossos.exe',
              icon='../../knossos/data/hlp.ico',
              debug=False,
              strip=None,
              upx=True,
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
                   upx=not debug,
                   name='Knossos')
