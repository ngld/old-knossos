# -*- mode: python -*-
import os

onefile = True

a = Analysis(['../manager.py'],
             pathex=[os.path.abspath('.')],
             hiddenimports=['urllib2', 'bisect'],
             hookspath=['.'],
             runtime_hooks=['PySide-rthook.py'])

# Exclude everything we don't need to get a smaller output. (This saves around 2 MB.)
idx = []
for i, item in enumerate(a.binaries):
    if item[0].startswith('PySide.') and item[0] not in ('PySide.QtCore', 'PySide.QtGui'):
        idx.append(i)
    elif item[0].startswith('Qt') and item[0] not in ('QtCore4.dll', 'QtGui4.dll'):
        idx.append(i)
    elif item[0].startswith('plugins') and not item[0].endswith('qjpeg4.dll'):
        idx.append(i)

for i in reversed(idx):
    del a.binaries[i]

# This saves around 0.3MB maybe it's not worth it...
idx = []
for i, item in enumerate(a.pure):
    if item[0].startswith('pydoc'):
        idx.append(i)

for i in reversed(idx):
    del a.pure[i]

pyz = PYZ(a.pure)

a.datas += [('7z.exe', '7z.exe', 'BINARY'), ('7z.dll', '7z.dll', 'BINARY'), ('commit', 'commit', 'DATA'), ('hlp.png', '../hlp.png', 'DATA')]

if onefile:
  exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
            exclude_binaries=False,
            name='fs2mod-py.exe',
            icon='../hlp.ico',
            debug=False,
            strip=None,
            upx=True,
            console=False )
else:
  exe = EXE(pyz,
            a.scripts,
            exclude_binaries=True,
            name='fs2mod-py.exe',
            icon='../hlp.ico',
            debug=False,
            strip=None,
            upx=True,
            console=False )
  coll = COLLECT(exe,
                 a.binaries,
                 a.zipfiles,
                 a.datas,
                 strip=None,
                 upx=True,
                 name='fs2mod-py')
