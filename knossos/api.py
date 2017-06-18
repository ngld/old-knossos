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
import json
import shlex
import glob

from . import uhf
uhf(__name__)

from . import center, util, launcher, integration
from .qt import QtCore, QtWidgets
from .tasks import run_task, CheckUpdateTask, CheckTask, FetchTask, UninstallTask
from .windows import ModSettingsWindow, ModInstallWindow
from .repo import ModNotFound
from .ipc import IPCComm
from .runner import run_fs2_silent, run_mod

# TODO: Split this file up into smaller parts and move them into the respective modules
# (i.e. run_mod should be in runner).

ipc_block = None
translate = QtCore.QCoreApplication.translate


def save_settings():
    center.settings['hash_cache'] = dict()
    for path, info in util.HASH_CACHE.items():
        # Skip deleted files
        if os.path.exists(path):
            center.settings['hash_cache'][path] = info

    with open(os.path.join(center.settings_path, 'settings.json'), 'w') as stream:
        json.dump(center.settings, stream)


def get_fso_flags():
    global fso_flags

    if center.settings['fs2_bin'] is None:
        return None

    if center.fso_flags is not None and center.fso_flags[0] == center.settings['fs2_bin']:
        return center.fso_flags[1]

    fs2_bin = os.path.join(center.settings['base_path'], 'bin', center.settings['fs2_bin'])
    if not os.path.isfile(fs2_bin):
        return None

    flags_path = os.path.join(center.settings['base_path'], 'flags.lch')
    rc = run_fs2_silent(['-get_flags', '-parse_cmdline_only'])

    flags = None

    if rc != 1 and rc != 0:
        logging.error('Failed to run FSO! (Exit code was %d)', rc)
    elif not os.path.isfile(flags_path):
        logging.error('Could not find the flags file "%s"!', flags_path)
    else:
        with open(flags_path, 'rb') as stream:
            flags = util.FlagsReader(stream)

    center.fso_flags = (center.settings['fs2_bin'], flags)
    return flags


def get_executables():
    exes = []

    for mid, mvs in center.installed.mods.items():
        for mod in mvs:
            for pkg in mod.packages:
                for item in pkg.executables:
                    name = mod.title + ' ' + item.get('version', '')
                    if item.get('debug', False):
                        name += ' (DEBUG)'

                    path = os.path.join(mod.folder, item['file'])
                    exes.append((name, path))

    bin_path = center.settings['base_path']
    if bin_path is not None:
        bin_path = os.path.abspath(os.path.join(bin_path, 'bin/custom'))
        if os.path.isdir(bin_path):
            if sys.platform == 'darwin':
                for app in glob.glob(os.path.join(bin_path, '*.app')):
                    name = os.path.basename(app)
                    exes.append((name, os.path.join(name, 'Contents', 'MacOS', name[:-4])))
            else:
                bins = glob.glob(os.path.join(bin_path, 'f*2_open_*'))

                for path in bins:
                    path = os.path.basename(path)

                    if not path.endswith(('.map', '.pdb')):
                        exes.append((path, path))

    return exes


def fetch_list():
    return run_task(FetchTask())


def get_cmdline(mod):
    if mod is None:
        return center.settings['cmdlines'].get('#default', [])[:]

    if mod.mid in center.settings['cmdlines']:
        return center.settings['cmdlines'][mod.mid][:]
    elif mod.cmdline != '':
        return shlex.split(mod.cmdline)
    else:
        return center.settings['cmdlines'].get('#default', [])[:]


def get_old_fso_profile_path():
    if sys.platform.startswith('linux'):
        leg_path = os.path.expanduser('~/.fs2_open')
    elif sys.platform == 'darwin':
        leg_path = os.path.expanduser('~/Library/FS2_Open')
    else:
        # TODO: This obviously won't work in most cases because we most likely won't be running FSO
        # from the base directory.
        leg_path = center.settings['base_path']

    return leg_path


_new_profile_path = None
def get_new_fso_profile_path():
    global _new_profile_path

    if _new_profile_path is None:
        try:
            _new_profile_path = util.check_output(launcher.get_cmd(['--fso-config-path'])).strip()
        except:
            logging.exception('Failed to retrieve FSO profile path from SDL!')
            _new_profile_path = 'None'

    return _new_profile_path


def get_fso_profile_path():
    path = get_new_fso_profile_path()
    leg_path = get_old_fso_profile_path()

    if leg_path and (path in ('', 'None') or
        (not os.path.exists(os.path.join(path, 'fs2_open.ini')) and os.path.exists(leg_path))
    ):
        profile_path = leg_path
    else:
        profile_path = path

    logging.info('Using profile path "%s".', profile_path)
    return profile_path


def read_fso_cmdline():
    # Look for the cmdline path.
    path = get_fso_profile_path()
    if path is None:
        return []

    path = os.path.join(path, 'data/cmdline_fso.cfg')

    # Read the current cmdline.
    cmdline = []
    if os.path.exists(path):
        try:
            with open(path, 'r') as stream:
                cmdline = shlex.split(stream.read().strip())
        except:
            logging.exception('Failed to read "%s", assuming empty cmdline.', path)

    for i, part in enumerate(cmdline):
        if part.strip() == '-mod':
            del cmdline[i]

            if len(cmdline) > i:
                del cmdline[i]

            break

    return cmdline


def check_retail_files():
    if center.settings['base_path'] is None:
        return

    has_retail = False
    fs2_path = os.path.join(center.settings['base_path'], 'FS2')
    if os.path.isdir(fs2_path):
        for item in os.listdir(fs2_path):
            if item.lower() == 'root_fs2.vp':
                has_retail = True
                break

    if has_retail:
        logging.debug('The FS2 path (%s) contains retail files!', center.settings['base_path'])
    else:
        logging.debug('The FS2 path (%s) does not contain retail files!', center.settings['base_path'])

    if has_retail != center.has_retail:
        center.has_retail = has_retail
        run_task(CheckTask())

    return has_retail


##############
# Public API #
##############


def get_mod(mid, version=None):
    if center.mods is None:
        QtWidgets.QMessageBox.critical(None, 'Knossos', translate('api', 'Hmm... I never got a mod list. Get a coder!'))
        return None
    else:
        try:
            return center.mods.query(mid, version)
        except ModNotFound:
            QtWidgets.QMessageBox.critical(None, 'Knossos', translate('api', 'Mod "%s" could not be found!') % mid)
            return None


# TODO: Create a proper window for this and move it to the windows module.
def uninstall_pkgs(pkgs, name=None, cb=None):
    titles = [pkg.name for pkg in pkgs if center.installed.is_installed(pkg)]

    if name is None:
        name = translate('api', 'these packages')

    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Question)
    msg.setText(translate('api', 'Do you really want to uninstall %s?') % name)
    msg.setInformativeText(translate('api', '%s will be removed.') % (', '.join(titles)))
    msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    msg.setDefaultButton(QtWidgets.QMessageBox.No)

    if msg.exec_() == QtWidgets.QMessageBox.Yes:
        task = UninstallTask(pkgs)
        if cb is not None:
            task.done.connect(cb)

        run_task(task)
        return True
    else:
        return False


#########
# Tools #
#########


def install_scheme_handler(interactive=True):
    logging.info('Installing scheme handler...')

    try:
        if integration.current.install_scheme_handler():
            if interactive:
                QtWidgets.QMessageBox.information(None, 'Knossos', translate('api', 'Done!'))
            return
    except:
        logging.exception('Failed to install the scheme handler!')

    QtWidgets.QMessageBox.critical(None, 'Knossos',
        translate('api', 'I probably failed to install the scheme handler.\nRun me as administrator and try again.'))


def setup_ipc():
    global ipc_block

    ipc_block = IPCComm(center.settings_path)
    ipc_block.messageReceived.connect(handle_ipc)
    ipc_block.listen()


def shutdown_ipc():
    global ipc_block

    if ipc_block:
        ipc_block.close()


def handle_ipc(msg):
    msg = msg.data().decode('utf8', 'ignore').strip()

    try:
        msg = json.loads(msg)
    except:
        logging.exception('Failed to parse IPC message %s.', msg)
        return

    if msg[0] == 'focus':
        center.main_win.win.activateWindow()
        center.main_win.win.raise_()
    elif msg[0] == 'run':
        if len(msg) < 2:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                translate('api.handle_ipc', 'The fso://run/<mod id> link is missing a parameter!'))
        else:
            mod = get_mod(msg[1])

            if mod is not None:
                run_mod(mod)
            else:
                QtWidgets.QMessageBox.critical(None, 'Knossos',
                    translate('api.handle_ipc', 'The mod "%s" was not found!') % msg[1])
    elif msg[0] == 'install':
        if len(msg) < 2:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                translate('api.handle_ipc', 'The fso://install/<mod id> link is missing a parameter!'))
            return

        mod = get_mod(msg[1])
        pkgs = []

        if not mod:
            # TODO: Maybe we should update the mod DB here?
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                translate('api.handle_ipc', 'The mod "%s" was not found!') % msg[1])
            return

        if len(msg) > 2:
            for pname in msg[2:]:
                for pkg in mod.packages:
                    if pkg.name == pname:
                        pkgs.append(pkg)

        center.main_win.win.activateWindow()

        if mod.mid not in center.installed.mods:
            ModInstallWindow(mod, pkgs)
        else:
            QtWidgets.QMessageBox.information(None, 'Knossos',
                translate('api.handle_ipc', 'Mod "%s" is already installed!') % (mod.title))
    elif msg[0] == 'settings':
        center.main_win.win.activateWindow()

        if len(msg) == 1 or msg[1] == '':
            center.main_win.show_fso_settings()
        else:
            mod = get_mod(msg[1])

            if mod is None or mod.mid not in center.installed.mods:
                if mod is None:
                    name = msg[1]
                else:
                    name = mod.title

                QtWidgets.QMessageBox.information(None, 'Knossos',
                    translate('api.handle_ipc', 'Mod "%s" is not yet installed!') % (name))
            else:
                ModSettingsWindow(mod)
    else:
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('api.handle_ipc', 'The action "%s" is unknown!') % (msg[0]))


def _read_default_cmdline():
    if '#default' not in center.settings['cmdlines']:
        center.settings['cmdlines']['#default'] = read_fso_cmdline()


def enable_raven():
    try:
        from raven import Client
    except ImportError:
        logging.exception('Failed to import raven!')
        return False

    from raven.transport.threaded_requests import ThreadedRequestsHTTPTransport
    from raven.handlers.logging import SentryHandler

    if hasattr(sys, 'frozen'):
        from six.moves.urllib.parse import quote as urlquote
        center.SENTRY_DSN += '&ca_certs=' + urlquote(os.path.join(sys._MEIPASS, 'requests', 'cacert.pem'))

    center.raven = Client(
        center.SENTRY_DSN,
        release=center.VERSION,
        environment='debug' if center.DEBUG else 'production',
        transport=ThreadedRequestsHTTPTransport
    )
    center.raven.tags_context({
        'os': sys.platform
    })
    center.raven_handler = SentryHandler(center.raven, level=logging.ERROR)
    logging.getLogger().addHandler(center.raven_handler)

    return True


def disable_raven():
    if center.raven_handler:
        logging.getLogger().removeHandler(center.raven_handler)

    center.raven = None
    center.raven_handler = None


def init_self():
    setup_ipc()
    center.signals.fs2_path_changed.connect(_read_default_cmdline)
    center.signals.fs2_path_changed.connect(check_retail_files)

    if center.settings['update_notify'] and not center.VERSION.endswith('-dev'):
        run_task(CheckUpdateTask())
