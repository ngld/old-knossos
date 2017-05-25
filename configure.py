## Copyright 2017 Knossos authors, see NOTICE file
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

sys.path.insert(0, os.path.abspath('tools/common'))

from ninja_syntax import Writer
from configlib import *

info('Collecting files...\n')

UI_FILES = [
    'ui/flags.ui',
    'ui/gogextract.ui',
    'ui/hell.ui',
    'ui/install.ui',
    'ui/log_viewer.ui',
    'ui/mod_settings.ui',
    'ui/mod_versions.ui',
    'ui/select_list.ui'
]

RCC_FILES = [
    'knossos/data/hlp.png'
] + \
    build_file_list('html') + \
    build_file_list('ui', ('*.png', '*.jpg', '*.css'))

RCC_FILES = [file for file in RCC_FILES if os.path.isfile(file)]

SRC_FILES = [
    'knossos/third_party/__init__.py',
    'knossos/third_party/cpuinfo.py',
    'knossos/ui/__init__.py',
    'knossos/__init__.py',
    'knossos/__main__.py',
    'knossos/api.py',
    'knossos/center.py',
    'knossos/clibs.py',
    'knossos/integration.py',
    'knossos/ipc.py',
    'knossos/launcher.py',
    'knossos/progress.py',
    'knossos/py2_compat.py',
    'knossos/qt.py',
    'knossos/repo.py',
    'knossos/runner.py',
    'knossos/tasks.py',
    'knossos/util.py',
    'knossos/web.py',
    'knossos/windows.py'
]


info('Checking Python version...')
if sys.hexversion < 0x20700 or (sys.hexversion > 0x30000 and sys.hexversion < 0x30200):
    fail('Need at least 2.7.0 or 3.2.0!')
else:
    info(' ok\n')

check_module('PyQt5')
check_module('semantic_version')
check_module('six')
check_module('requests')
if sys.platform == 'win32':
    check_module('comtypes')

pyuic = try_program([[sys.executable, '-mPyQt5.uic.pyuic'], ['pyuic5'], ['pyuic']], 'pyuic')
pylupdate = try_program([[sys.executable, '-mPyQt5.pylupdate_main'], ['pylupdate5'], ['pylupdate']], 'pylupdate', test_param='-version')

lupdate = find_program(['lupdate-qt5', 'lupdate'], 'lupdate')
# lrelease = find_program(['lrelease-qt5', 'lrelease'], 'lrelease')
rcc = find_program(['rcc-qt5', 'rcc'], 'rcc')
find_program(['7z', '7za'], '7zip')

check_ctypes_lib(['libSDL2-2.0.so.0', 'SDL2', 'SDL2.dll', 'libSDL2.dylib'], 'SDL2')
check_ctypes_lib(['libopenal.so.1.15.1', 'openal', 'OpenAL'], 'OpenAL')

os.chdir(os.path.abspath(os.path.dirname(__file__)))
info('Writing build.ninja...\n')

with open(os.path.join('build.ninja'), 'w') as stream:
    n = Writer(stream)

    n.comment('Transformers')
    n.rule('uic', py_script('tools/common/uic.py', ['$in', '$out'] + pyuic), 'UIC $out')
    n.rule('rcc', py_script('tools/common/rcc.py', [rcc, '$out', '$in']), 'RCC $out')
    n.rule('js_lupdate', py_script('tools/common/js_lupdate.py', ['-o', '$out', '$in']), 'JS-LUPDATE $out')
    n.rule('pylupdate', cmd2str(pylupdate + ['$in', '-ts', '$out']), 'PY-LUPDATE $out')
    n.rule('lupdate', cmd2str([lupdate, '$in', '-ts', '$out']), 'LUPDATE $out')

    n.comment('Files')
    ui_targets = build_targets(n, UI_FILES, 'uic', new_ext='py', new_path='knossos/ui')
    n.build('knossos/data/resources.rcc', 'rcc', RCC_FILES)
    n.build('html/js/modlist_ts.js', 'js_lupdate', ['html/js/modlist.js', 'html/index.html'])
    n.build('locale/_py.ts', 'pylupdate', SRC_FILES)
    n.build('locale/_ui.ts', 'lupdate', ['locale/_py.ts', 'html/js/modlist_ts.js'] + UI_FILES)

    n.build('resources', 'phony', ui_targets + ['knossos/data/resources.rcc', 'html/js/modlist_ts.js'])

    n.comment('Scripts')
    n.rule('regen', py_script('configure.py', sys.argv[1:]), 'RECONFIGURE', generator=True)
    n.build('build.ninja', 'regen', 'configure.py')

    setup_args = ['sdist']
    if check_module('wheel', required=False):
        setup_args.append('bdist_wheel')

    n.rule('dist', py_script('setup.py', setup_args), 'SDIST', pool='console')
    n.build('dist', 'dist', 'resources')

    n.rule('run', py_script('knossos/__main__.py'), 'RUN', pool='console')
    n.build('run', 'run', 'resources')

    n.rule('debug', cmdenv(py_script('knossos/__main__.py'), {'KN_DEBUG': 1}), 'DEBUG', pool='console')
    n.build('debug', 'debug', 'resources')

    if sys.platform == 'win32':
        n.comment('Win32')
        
        if check_module('PyInstaller', required=False):
            pyinstaller = 'cmd /C "cd releng\\windows" && ' + cmd2str([sys.executable, '-OO', '-mPyInstaller', '-d', '--distpath=.\\dist', '--workpath=.\\build', 'Knossos.spec', '-y'])
            n.rule('pyinstaller', pyinstaller, 'PACKAGE', pool='console')
            n.build('build', 'pyinstaller', ['resources'] + SRC_FILES)

        nsis = find_program(['makensis', r'C:\Program Files (x86)\NSIS\makensis.exe', r'C:\Program Files\NSIS\makensis.exe'], 'NSIS', required=False)
        if nsis:
            version = 'TODO'
            n.rule('nsis', cmd2str([nsis, '/NOCD', r'/DKNOSSOS_ROOT=.\\', '/DKNOSSOS_VERSION=%s' % version, '$in']), 'NSIS')
            n.build('releng/windows/nsis/installer.nsi', 'nsis', 'build')
            n.build('releng/windows/nsis/updater.nsi', 'nsis', 'build')
            
            n.build('installer', 'phony', ['releng/windows/nsis/installer.nsi', 'releng/windows/nsis/updater.nsi'])

info('\nDone! Use "ninja run" to start Knossos.\n')
