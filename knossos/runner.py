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

from __future__ import absolute_import, print_function

import sys
import os
import logging
import re
import threading
import subprocess
import time
import ctypes.util
import stat
import shutil
import six

from . import center, repo, api, util
from .qt import QtCore, QtWidgets

# TODO: What happens if a SONAME contains a space?
FILE_PATH_RE = r'[a-zA-Z0-9\./\-\_\+]+'
LDD_RE = re.compile(r'\s*(' + FILE_PATH_RE + r') (?:=> (not found|' + FILE_PATH_RE + r'))?(?: \([^\)]+\))?\s*')
LIB_RE = re.compile(r'lib([a-zA-Z0-9\.\-\_\+]+)\.so(?:\..*)?')
LDCONF_RE = re.compile(r'\s*(' + FILE_PATH_RE + r') \([^\)]+\) => (' + FILE_PATH_RE + r')')
_LIB_CACHE = None

fs2_watcher = None
fred_watcher = None
translate = QtCore.QCoreApplication.translate


class SignalContainer(QtCore.QObject):
    signal = QtCore.Signal(list)


# This wrapper makes sure that the wrapped function is always run in the QT main thread.
def run_in_qt(func):
    cont = SignalContainer()

    def dispatcher(*args):
        cont.signal.emit(list(args))

    def listener(params):
        func(*params)

    cont.signal.connect(listener)

    return dispatcher


class Fs2Watcher(threading.Thread):
    _params = None
    _fred = False
    _key_layout = None

    def __init__(self, params, fred=False):
        super(Fs2Watcher, self).__init__()

        self._params = params
        self._fred = fred
        self.daemon = True
        self.start()

    def run(self):
        global fs2_watcher

        old_path = None
        fs2_bin = self._params[0]
        basepath = os.path.join(center.settings['base_path'], 'FSO')

        if not os.path.isfile(fs2_bin):
            self.fs2_missing_msg(fs2_bin)
            return

        mode = os.stat(fs2_bin).st_mode
        if mode & stat.S_IXUSR != stat.S_IXUSR:
            # Make it executable.
            os.chmod(fs2_bin, mode | stat.S_IXUSR)

        env = os.environ.copy()
        if sys.platform.startswith('linux'):
            ld_path, missing = fix_missing_libs(fs2_bin)
            if len(missing) > 0:
                self.complain_missing(missing)
                return

            env['LD_LIBRARY_PATH'] = ld_path

        if center.settings['keyboard_setxkbmap']:
            self.set_us_layout()

        logging.debug('Launching FS2: %s', [fs2_bin] + self._params[1:])

        if sys.platform.startswith('win'):
            if os.path.basename(fs2_bin) != fs2_bin:
                # On Windows, the FSO engine changes the CWD to the directory the EXE file is in.
                # Since the fs2_bin is in a subdirectory we'll have to copy it!
                old_path = fs2_bin
                fs2_bin = os.path.join(basepath, '__tmp_' + os.path.basename(old_path))

                shutil.copy2(old_path, fs2_bin)

                # Make sure FSO still finds any DLL files located in the original EXE's folder.
                old_parent = os.path.abspath(os.path.dirname(old_path))
                if 'PATH' in env:
                    env['PATH'] = old_parent + os.pathsep + env['PATH']
                else:
                    env['PATH'] = old_parent

                if six.PY2:
                    env['PATH'] = env['PATH'].encode('utf8')

        fail = False
        rc = -999
        reason = '???'
        try:
            p = subprocess.Popen([fs2_bin] + self._params[1:], cwd=basepath, env=env)

            time.sleep(0.3)
            if p.poll() is not None:
                rc = p.returncode
                reason = 'return code: %d' % rc
                fail = True
        except OSError as exc:
            logging.exception('Failed to launch FS2!')
            reason = str(exc).decode('utf8', 'replace')
            fail = True

        if fail:
            self.cleanup(fs2_bin, old_path)
            center.signals.fs2_failed.emit(rc)
            self.failed_msg(reason)
            return

        center.signals.fs2_launched.emit()
        p.wait()
        self.cleanup(fs2_bin, old_path)
        center.signals.fs2_quit.emit()

    @run_in_qt
    def failed_msg(self, reason):
        msg = translate('runner', 'Starting FS2 Open (%s) failed! (%s)') % (
            os.path.join(center.settings['fs2_path'], center.settings['fs2_bin']), reason)
        QtWidgets.QMessageBox.critical(center.app.activeWindow(), translate('runner', 'Failed'), msg)

    @run_in_qt
    def fs2_missing_msg(self, fs2_bin):
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('runner', 'I can\'t find FSO! (The file "%s" is missing!)') % fs2_bin)

    @run_in_qt
    def complain_missing(self, missing):
        if len(missing) > 1:
            msg = translate('runner', "I can't start FSO because the libraries %s are missing!")
        else:
            msg = translate('runner', "I can't start FSO because the library %s is missing!")

        QtWidgets.QMessageBox.critical(None, 'Knossos', msg % util.human_list(missing))

    def set_us_layout(self):
        key_layout = util.check_output(['setxkbmap', '-query'])
        self._key_layout = key_layout.splitlines()[2].split(':')[1].strip()

        util.call(['setxkbmap', '-layout', 'us'])

    def cleanup(self, fs2_bin, old_path=None):
        if self._key_layout is not None:
            util.call(['setxkbmap', '-layout', self._key_layout])

        if sys.platform.startswith('win') and old_path is not None:
            # Cleanup
            retries = 3

            while retries > 0:
                try:
                    os.unlink(fs2_bin)
                except:
                    logging.exception('Failed to delete FSO file "%s"!', fs2_bin)

                if os.path.isfile(fs2_bin):
                    time.sleep(1)
                    retries -= 1
                else:
                    break


def check_elf_libs(fpath):
    out = util.check_output(['ldd', fpath], env={'LANG': 'C'}).splitlines()
    libs = {}

    for r_line in out:
        line = LDD_RE.match(r_line)
        if not line:
            logging.warning('Failed to parse ldd line "%s"!', r_line)
            continue

        if line.group(2) == 'not found':
            libs[line.group(1)] = None
        elif not line.group(2):
            # This is most likely a line like "linux-vdso.so.1 (0x00007fff847fe000)" which we can ignore.
            continue
        else:
            libs[line.group(1)] = line.group(2)

    return libs


def get_lib_path(filename):
    global _LIB_CACHE

    if not _LIB_CACHE:
        _LIB_CACHE = {}

        try:
            env = os.environ.copy()
            env['LANG'] = 'C'
            data = util.check_output(['ldconfig', '-p'], env=env).splitlines()
        except subprocess.CalledProcessError:
            logging.exception('Failed to run ldconfig!')
            return None

        for line in data[1:]:
            m = LDCONF_RE.match(line)
            if not m:
                logging.warning('Failed to parse ldconfig line "%s"!', line)
                continue

            _LIB_CACHE[m.group(1)] = m.group(2)

    return _LIB_CACHE.get(filename)


def fix_missing_libs(fpath, augment_ldpath=True):
    base = os.path.dirname(fpath)
    patch_dir = os.path.join(base, '__k_plibs')

    libs = check_elf_libs(fpath)
    missing = []
    for name, path in libs.items():
        if not path:
            missing.append(name)

    if len(missing) == 0:
        # Yay, nothing to do.
        if augment_ldpath:
            return os.environ.get('LD_LIBRARY_PATH', ''), missing
        else:
            return '', missing

    for lib in missing[:]:
        p_name = os.path.join(patch_dir, lib)
        if os.path.exists(p_name):
            missing.remove(lib)
        else:
            ld_name = LIB_RE.match(lib)
            if ld_name:
                fixed_name = get_lib_path(ctypes.util.find_library(ld_name.group(1)))
                if fixed_name:
                    if not os.path.isdir(patch_dir):
                        os.mkdir(patch_dir)

                    os.symlink(fixed_name, p_name)
                    missing.remove(lib)

    if augment_ldpath:
        ld_path = os.environ.get('LD_LIBRARY_PATH', '')
        if ld_path != '':
            patch_dir += ':' + ld_path

    return patch_dir, missing


def run_fs2(params=None):
    global fs2_watcher

    if fs2_watcher is None or not fs2_watcher.is_alive():
        fs2_watcher = Fs2Watcher(params)
        return True
    else:
        return False


def run_fred(params=None):
    global fred_watcher

    if not center.settings['fred_bin']:
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('runner', 'No FRED executable selected. Please go to Settings > Game settings and select one.'))
        return

    fred_path = os.path.join(center.settings['fs2_path'], center.settings['fred_bin'])
    if not os.path.isfile(fred_path):
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('runner', 'The selected FRED executable was not found!' +
                ' Please go to Settings > Game settings and select one.'))
        return

    if fred_watcher is None or not fred_watcher.is_alive():
        fred_watcher = Fs2Watcher(params, fred=True)
        return True
    else:
        return False


def run_fs2_silent(params):
    base_path = center.settings['base_path']
    fs2_bin = os.path.join(base_path, 'bin', center.settings['fs2_bin'])

    if not os.path.isfile(fs2_bin):
        return -128

    mode = os.stat(fs2_bin).st_mode
    if mode & stat.S_IXUSR != stat.S_IXUSR:
        # Make it executable.
        os.chmod(fs2_bin, mode | stat.S_IXUSR)

    env = {}
    if sys.platform.startswith('linux'):
        ld_path, missing = fix_missing_libs(fs2_bin)
        if len(missing) > 0:
            return -127

        env['LD_LIBRARY_PATH'] = ld_path

    try:
        rc = util.call([fs2_bin] + params, cwd=base_path, env=env)
    except OSError:
        return -129

    if rc == 3221225595:
        # We're missing a DLL
        return -127


def run_mod(mod, fred=False, debug=False):
    global installed

    if mod is None:
        mod = repo.Mod()

    mods = []

    try:
        inst_mod = center.installed.query(mod)
    except repo.ModNotFound:
        inst_mod = None

    if not inst_mod:
        QtWidgets.QMessageBox.critical(None, translate('runner', 'Error'),
            translate('runner', 'The mod "%s" could not be found!') % mod)
        return

    try:
        mods = mod.get_mod_flag()
    except repo.ModNotFound as exc:
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('runner', 'Sorry, I can\'t start this mod because its dependency "%s" is missing!') % exc.mid)
        return

    if mods is None:
        return

    try:
        exes = mod.get_executables()
    except Exception:
        logging.exception('Failed to retrieve binaries for "%s"!' % mod.mid)
        QtWidgets.QMessageBox.critical(None, translate('runner', 'Error'),
            translate('runner', 'I couldn\'t find a FS2 executable. Can\'t run FS2!!'))
        return

    binpath = None
    for item in exes:
        if item.get('fred', False) == fred and item['debug'] == debug:
            binpath = item['file']
            break

    if not binpath:
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('runner', 'No matching executable was found!'))
        return

    # Look for the cmdline path.
    path = os.path.join(api.get_fso_profile_path(), 'data/cmdline_fso.cfg')
    cmdline = mod.cmdline

    if len(mods) > 0 and '-mod' not in cmdline:
        cmdline.append('-mod')
        cmdline.append(','.join(mods))

    if not os.path.isfile(path):
        basep = os.path.dirname(path)
        if not os.path.isdir(basep):
            os.makedirs(basep)

    try:
        with open(path, 'w') as stream:
            stream.write(stringify_cmdline(cmdline))
    except:
        logging.exception('Failed to modify "%s". Not starting FS2!!', path)

        QtWidgets.QMessageBox.critical(None, translate('runner', 'Error'),
            translate('runner', 'Failed to edit "%s"! I can\'t change the current mod!') % path)
    else:
        logging.info('Starting mod "%s" with cmdline "%s".', mod.title, cmdline)
        run_fs2([binpath])


def stringify_cmdline(line):
    result = []
    for part in line:
        if '"' in part:
            raise Exception("It's impossible to pass double quotes to FSO!")

        if ' ' in part:
            part = '"%s"' % part

        result.append(part)

    return ' '.join(result)
