# -*- mode: python -*-

import os.path

onefile = False
him = []

# Make sure all paths that end up in the compiled executable are relative.
pd = config['PYZ_dependencies']
for i, item in enumerate(pd):
    if 'Z:' in item[1]:
        pd[i] = (item[0], os.path.relpath(item[1]), item[2])

# Build the TaskbarLib module.
try:
    import comtypes.client as cc
    cc.GetModule('support/taskbar.tlb')

    him.append('comtypes.gen.TaskbarLib')
except:
    import logging
    logging.exception('Failed to generate comtypes.gen.TaskbarLib!')


a = Analysis(['../../knossos/__main__.py'],
             pathex=['../..'],
             hiddenimports=him,
             hookspath=['../common'],
             runtime_hooks=['../common/PySide-rthook.py'])

# Exclude everything we don't need.
idx = []
for i, item in enumerate(a.binaries):
    if item[0].startswith('PySide.') and item[0] not in ('PySide.QtCore', 'PySide.QtGui', 'PySide.QtNetwork', 'PySide.QtWebKit'):
        idx.append(i)
    elif item[0].startswith('Qt') and item[0] not in ('QtCore4.dll', 'QtGui4.dll', 'QtNetwork4.dll', 'QtWebKit4.dll'):
        idx.append(i)
    elif item[0].startswith('plugins') and not item[0].endswith(('qjpeg4.dll', 'qgif4.dll')):
        idx.append(i)
    elif item[0].startswith('ole') or item[0].startswith('user32'):
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

a.datas += [('7z.exe', 'support/7z.exe', 'BINARY'),
            ('7z.dll', 'support/7z.dll', 'BINARY'),
            ('version', 'version', 'DATA'),
            ('data/hlp.ico', '../../knossos/data/hlp.ico', 'DATA'),
            ('data/resources.rcc', '../../knossos/data/resources.rcc', 'DATA'),
            ('SDL.dll', 'support/SDL.dll', 'BINARY'),
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
              console=False)
else:
    exe = EXE(pyz,
              a.scripts,
              exclude_binaries=True,
              name='Knossos.exe',
              icon='../../knossos/data/hlp.ico',
              debug=False,
              strip=None,
              upx=True,
              console=True)
    
    coll = COLLECT(exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   strip=None,
                   upx=True,
                   name='Knossos')
