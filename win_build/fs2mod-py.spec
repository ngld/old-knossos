# -*- mode: python -*-
import os

#path = os.path.abspath(os.path.dirname(__file__))
onefile = True

a = Analysis(['../installer.py'],
             pathex=['.'],
             hiddenimports=['urllib2', 'bisect'],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)

# Replace PySide's QtGui4.dll and QtCore4.dll with our statically linked versions.
for i, item in enumerate(a.binaries):
  if item[2] == 'BINARY' and item[0] in ('QtGui4.dll', 'QtCore4.dll'):
    a.binaries[i] = (item[0], './' + item[0], 'BINARY')
    
a.datas += [('7z.exe', '7z.exe', 'BINARY'), ('7z.dll', '7z.dll', 'BINARY'), ('commit', 'commit', 'DATA')]

if onefile:
  exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
            exclude_binaries=False,
            name='fs2mod-py.exe',
            icon='hlp.ico',
            debug=False,
            strip=None,
            upx=True,
            console=True)
else:
  exe = EXE(pyz,
            a.scripts,
            exclude_binaries=True,
            name='fs2mod-py.exe',
            icon='hlp.ico',
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
