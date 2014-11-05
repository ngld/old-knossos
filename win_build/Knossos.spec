# -*- mode: python -*-
import os

onefile = False

a = Analysis(['../knossos/__main__.py'],
             pathex=['.'],
             hiddenimports=[],
             hookspath=['.'],
             runtime_hooks=['PySide-rthook.py'])

# Exclude everything we don't need.
idx = []
for i, item in enumerate(a.binaries):
    if item[0].startswith('PySide.') and item[0] not in ('PySide.QtCore', 'PySide.QtGui', 'PySide.QtNetwork', 'PySide.QtWebKit'):
        idx.append(i)
    elif item[0].startswith('Qt') and item[0] not in ('QtCore4.dll', 'QtGui4.dll', 'QtNetwork4.dll', 'QtWebKit4.dll'):
        idx.append(i)
    elif item[0].startswith('plugins') and not item[0].endswith('qjpeg4.dll'):
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

a.datas += [('7z.exe', '7z.exe', 'BINARY'),
            ('7z.dll', '7z.dll', 'BINARY'),
            ('version', 'version', 'DATA'),
            ('data/hlp.ico', '../knossos/data/hlp.ico', 'DATA'),
            ('data/resources.rcc', '../knossos/data/resources.rcc', 'DATA'),
            ('SDL.dll', 'SDL.dll', 'BINARY'),
            ('openal.dll', 'openal.dll', 'BINARY'),
            ('taskbar.tlb', 'taskbar.tlb', 'BINARY')]


if onefile:
  exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
            exclude_binaries=False,
            name='Knossos.exe',
            icon='../knossos/data/hlp.ico',
            debug=False,
            strip=None,
            upx=True,
            console=False )
else:
  exe = EXE(pyz,
            a.scripts,
            exclude_binaries=True,
            name='Knossos.exe',
            icon='../knossos/data/hlp.ico',
            debug=False,
            strip=None,
            upx=True,
            console=True )
  coll = COLLECT(exe,
                 a.binaries,
                 a.zipfiles,
                 a.datas,
                 strip=None,
                 upx=True,
                 name='Knossos')
