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
import json
from subprocess import CalledProcessError

from . import center, repo, util, settings
from .qt import QtCore, QtWidgets, run_in_qt

# TODO: What happens if a SONAME contains a space?
FILE_PATH_RE = r'[a-zA-Z0-9\./\-\_\+]+'
LDD_RE = re.compile(r'\s*(' + FILE_PATH_RE + r') (?:=> (not found|' + FILE_PATH_RE + r'))?(?: \([^\)]+\))?\s*')
LIB_RE = re.compile(r'lib([a-zA-Z0-9\.\-\_\+]+)\.so(?:\..*)?')
LDCONF_RE = re.compile(r'\s*(' + FILE_PATH_RE + r') \([^\)]+\) => (' + FILE_PATH_RE + r')')
_LIB_CACHE = None

watchers = []
translate = QtCore.QCoreApplication.translate


class Fs2Watcher(threading.Thread):
    _params = None
    _cwd = None

    def __init__(self, params, cwd):
        super(Fs2Watcher, self).__init__()

        self._params = params
        self._cwd = cwd
        self.daemon = True
        self.start()

        watchers.append(self)

    def run(self):
        try:
            fs2_bin = os.path.normpath(self._params[0])

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

            logging.debug('Launching FS2: %s in %s', repr([fs2_bin] + self._params[1:]), self._cwd)
            settings.ensure_fso_config()

            fail = False
            rc = -999
            reason = '???'
            try:
                p = subprocess.Popen([fs2_bin] + self._params[1:], cwd=self._cwd, env=env)

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
                center.signals.fs2_failed.emit(rc)
                self.failed_msg(reason, fs2_bin)
                return

            center.signals.fs2_launched.emit()
            p.wait()
            center.signals.fs2_quit.emit()
        finally:
            watchers.remove(self)

    @run_in_qt
    def failed_msg(self, reason, fs2_bin):
        msg = translate('runner', 'Starting %s failed! (%s)') % (fs2_bin, reason)
        QtWidgets.QMessageBox.critical(None, translate('runner', 'Failed'), msg)

    @run_in_qt
    def fs2_missing_msg(self, fs2_bin):
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('runner', 'I can\'t find the selected executable! (The file "%s" is missing!)') % fs2_bin)

    @run_in_qt
    def complain_missing(self, missing):
        if len(missing) > 1:
            msg = translate('runner', "I can't start because the libraries %s are missing!")
        else:
            msg = translate('runner', "I can't start because the library %s is missing!")

        QtWidgets.QMessageBox.critical(None, 'Knossos', msg % util.human_list(missing))


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


def run_fs2_silent(params):
    base_path = center.settings['base_path']
    fs2_bin = params[0]

    if not os.path.isfile(fs2_bin):
        return -128, None

    mode = os.stat(fs2_bin).st_mode
    if mode & stat.S_IXUSR != stat.S_IXUSR:
        # Make it executable.
        os.chmod(fs2_bin, mode | stat.S_IXUSR)

    # We copy the existing environment to avoid omitting any values that may be necessary for running the binary
    # properly
    env = dict(os.environ)
    # AppImages are a bit special since they are themselves ELF executables which contain the actual FSO executable so
    # it makes no sense to examine the binary for missing libraries
    if sys.platform.startswith('linux') and not fs2_bin.lower().endswith(".appimage"):
        ld_path, missing = fix_missing_libs(fs2_bin)
        if len(missing) > 0:
            return -127, None

        env['LD_LIBRARY_PATH'] = ld_path

    try:
        try:
            output = util.check_output(params, env=env, cwd=base_path, stderr=subprocess.DEVNULL)
            rc = 0
        except CalledProcessError as e:
            # check_output raises this error if the return code was anything other than 0
            rc = e.returncode
            output = e.output
    except OSError:
        return -129, None

    if rc == 3221225595:
        # We're missing a DLL
        return -127, None

    return rc, output


def run_mod(mod, tool=None, exe_label=None):
    global installed

    if mod is None:
        mod = repo.Mod()

    try:
        inst_mod = center.installed.query(mod)
    except repo.ModNotFound:
        inst_mod = None

    if not inst_mod:
        QtWidgets.QMessageBox.critical(None, translate('runner', 'Error'),
            translate('runner', 'The mod "%s" could not be found!') % mod)
        return

    if tool:
        try:
            exes = tool.get_executables()
        except Exception:
            logging.exception('Failed to retrieve binaries for "%s"!' % tool.mid)
            QtWidgets.QMessageBox.critical(None, translate('runner', 'Error'),
                translate('runner', "I couldn't find the tool's executables! Aborted."))
            return
    else:
        try:
            exes = mod.get_executables(user=True)
        except Exception:
            logging.exception('Failed to retrieve binaries for "%s"!' % mod.mid)
            QtWidgets.QMessageBox.critical(None, translate('runner', 'Error'),
                translate('runner', "I couldn't find an executable. Aborted."))
            return

    exes = [item for item in exes if item.get('label', None) == exe_label]
    if len(exes) == 0:
        logging.error('"%s" provided no valid executable.' % (tool or mod).mid)
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('runner', 'No matching executable was found!'))
        return

    try:
        mod_flag, mod_choice = mod.get_mod_flag()
    except repo.ModNotFound:
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('runner', '"%s" has an error in its dependencies. Aborted.' % mod))
        return

    if mod_choice:
        # We have to ask the user
        center.main_win.browser_ctrl.bridge.showLaunchPopup.emit(json.dumps({
            'id': mod.mid,
            'version': str(mod.version),
            'title': mod.title,
            'exes': [(x['file'], '%s - %s' % (x['mod'].title, os.path.basename(x['file']))) for x in exes],
            'mod_flag': mod_flag
        }))
    else:
        run_mod_ex(mod, exes[0]['file'], [path for path, label in mod_flag])


def run_mod_ex(mod, binpath, mod_flag):
    # Put the cmdline together
    cmdline = mod.cmdline

    if mod.user_cmdline:
        cmdline = mod.user_cmdline

    if mod.mtype == 'mod':
        parent = mod.get_parent()

        if parent.mid == 'FS2':
            basepath = parent.folder
        else:
            basepath = os.path.dirname(parent.folder)

            found = False
            for pkg in mod.packages:
                for dep in pkg.dependencies:
                    if dep['id'] == parent.mid:
                        found = True
                        break

                if found:
                    break

            if not found:
                logging.debug("Mod %s doesn't depend on parent, fixing mod flags...", mod)
                mod_flag.extend([p[0] for p in parent.get_mod_flag()[0]])
    elif mod.mtype:
        basepath = mod.folder

    if len(mod_flag) > 0:
        # The paths for -mod must be relative to the base path.
        # TODO: Do we have to make sure that there are no special characters here or are the rules for mod.folder and
        #       pkg.folder enough to assure that?
        cmdline += ' -mod ' + ','.join([os.path.relpath(p, basepath) for p in mod_flag])

    # Look for the cmdline path.
    path = os.path.join(settings.get_fso_profile_path(), 'data/cmdline_fso.cfg')

    # Create the containing folders if they are missing.
    if not os.path.isfile(path):
        basep = os.path.dirname(path)
        if not os.path.isdir(basep):
            os.makedirs(basep)

    try:
        with open(path, 'w') as stream:
            stream.write(cmdline)
    except Exception:
        logging.exception('Failed to modify "%s". Not starting!!', path)

        QtWidgets.QMessageBox.critical(None, translate('runner', 'Error'),
            translate('runner', 'Failed to edit "%s"! I can\'t change the current mod!') % path)
    else:
        logging.info('Starting mod "%s" with cmdline "%s" and tool "%s".', mod.title, cmdline, binpath)
        Fs2Watcher([binpath], cwd=basepath)


def stringify_cmdline(line):
    result = []
    for part in line:
        if '"' in part:
            raise Exception("It's impossible to pass double quotes to FSO!")

        if ' ' in part:
            part = '"%s"' % part

        result.append(part)

    return ' '.join(result)
