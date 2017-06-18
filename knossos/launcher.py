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
import subprocess
import time
import json
import traceback
import six
from six.moves.urllib import parse as urlparse

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')

# We have to be in the correct directory *before* we import clibs so we're going to do this as early as possible.
if hasattr(sys, 'frozen'):
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)
    else:
        os.chdir(os.path.dirname(sys.executable))
else:
    my_path = os.path.dirname(__file__)
    if my_path != '':
        os.chdir(my_path)


from . import center

# Initialize the FileHandler early to capture all log messages.
if not os.path.isdir(center.settings_path):
    os.makedirs(center.settings_path)

# We truncate the log file on every start to avoid filling the user's disk with useless data.
log_path = os.path.join(center.settings_path, 'log.txt')

try:
    if os.path.isfile(log_path):
        os.unlink(log_path)
except:
    # This will only be visible if the user is running a console version.
    logging.exception('The log is in use by someone!')
else:
    handler = logging.FileHandler(log_path, 'w')
    handler.setFormatter(logging.Formatter('%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s'))
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)

if not center.DEBUG:
    logging.getLogger().setLevel(logging.INFO)

if six.PY2:
    from . import py2_compat

from .qt import QtCore, QtGui, QtWidgets, variant as qt_variant
from .ipc import IPCComm
from . import util


app = None
ipc = None
translate = QtCore.QCoreApplication.translate


def my_excepthook(type, value, tb):
    try:
        # NOTE: This can fail (for some reason) in traceback.print_exception.
        logging.error('UNCAUGHT EXCEPTION!', exc_info=(type, value, tb))
    except:
        logging.error('UNCAUGHT EXCEPTION!\n%s%s: %s' % (''.join(traceback.format_tb(tb)), type.__name__, value))


def get_cmd(args=[]):
    if hasattr(sys, 'frozen') and sys.frozen == 1:
        my_path = [os.path.abspath(sys.executable)]
    else:
        my_path = os.path.realpath(os.path.abspath(__file__))
        my_path = [os.path.abspath(sys.executable), os.path.join(os.path.dirname(my_path), '__main__.py')]

    return my_path + args


def get_file_path(name):
    if hasattr(sys, 'frozen') and sys.frozen == 1:
        return os.path.join('data', name)

    my_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
    data_path = os.path.join(my_path, 'data')
    if os.path.isdir(data_path):
        return os.path.join(data_path, name)
    else:
        from pkg_resources import resource_filename
        return resource_filename(__package__, name)


def load_settings():
    from . import api

    spath = os.path.join(center.settings_path, 'settings.json')
    settings = center.settings
    if os.path.exists(spath):
        defaults = settings.copy()

        try:
            with open(spath, 'r') as stream:
                settings.update(json.load(stream))
        except:
            logging.exception('Failed to load settings from "%s"!', spath)

        # Migration
        if 's_version' not in settings or settings['s_version'] < 2:
            settings['repos'] = defaults['repos']
            settings['s_version'] = 2

        if settings['s_version'] < 3:
            if 'mods' in settings:
                del settings['mods']
            if 'installed_mods' in settings:
                del settings['installed_mods']

            settings['s_version'] = 3

        if settings['s_version'] < 4:
            settings['repos'] = defaults['repos']
            settings['s_version'] = 4

        del defaults
    else:
        # Most recent settings version
        settings['s_version'] = 4

    if settings['hash_cache'] is not None:
        util.HASH_CACHE = settings['hash_cache']

    if settings['use_raven']:
        api.enable_raven()

    return settings


def run_knossos():
    global app

    from . import repo, progress, api, integration
    from .windows import HellWindow

    if sys.platform.startswith('win') and os.path.isfile('7z.exe'):
        util.SEVEN_PATH = os.path.abspath('7z.exe')
    elif sys.platform == 'darwin' and os.path.isfile('7z'):
        util.SEVEN_PATH = os.path.abspath('7z')

    translate = QtCore.QCoreApplication.translate

    if not util.test_7z():
        QtWidgets.QMessageBox.critical(None, 'Error', translate(
            'launcher', 'I can\'t find "7z"! Please install it and run this program again.'),
            QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
        return

    util.DL_POOL.set_capacity(center.settings['max_downloads'])

    center.app = app
    center.installed = repo.InstalledRepo()
    center.pmaster = progress.Master()
    center.pmaster.start_workers(10)
    center.mods = repo.Repo()

    integration.init()
    api.check_retail_files()
    mod_db = os.path.join(center.settings_path, 'mods.json')
    if os.path.isfile(mod_db):
        center.mods.load_json(mod_db)

    center.main_win = HellWindow()
    center.main_win.open()
    app.exec_()

    api.save_settings()
    api.shutdown_ipc()


def handle_ipc_error():
    global app, ipc

    logging.warning('Failed to connect to main process!')

    if ipc is not None:
        ipc.clean()
        ipc = None


def scheme_handler(link):
    global app, ipc

    if not link.startswith(('fs2://', 'fso://')):
        # NOTE: fs2:// is deprecated, we don't tell anyone about it.
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('launcher', 'I don\'t know how to handle "%s"! I only know fso:// .') % (link))
        app.quit()
        return True

    link = urlparse.unquote(link.strip()).split('/')

    if len(link) < 3:
        QtWidgets.QMessageBox.critical(None, 'Knossos', translate('launcher', 'Not enough arguments!'))
        app.quit()
        return True

    if not ipc.server_exists():
        # Launch the program.
        subprocess.Popen(get_cmd())

        # Wait for the program...
        start = time.time()
        while not ipc.server_exists():
            if time.time() - start > 20:
                # That's too long!
                QtWidgets.QMessageBox.critical(None, 'Knossos', translate('launcher', 'Failed to start server!'))
                app.quit()
                return True

            time.sleep(0.3)

    try:
        ipc.open_connection(handle_ipc_error)
    except:
        logging.exception('Failed to connect to myself!')
        handle_ipc_error()
        return False

    if not ipc:
        return False

    ipc.send_message(json.dumps(link[2:]))
    ipc.close(True)
    app.quit()
    return True


def main():
    global ipc, app

    # Default to replacing errors when de/encoding.
    import codecs

    codecs.register_error('strict', codecs.replace_errors)
    codecs.register_error('really_strict', codecs.strict_errors)

    sys.excepthook = my_excepthook

    # The version file is only read in dev builds.
    if center.VERSION.endswith('-dev') and os.path.isfile('version'):
        with open('version', 'r') as data:
            version = data.read().strip()

            if version != center.VERSION:
                if version.startswith(center.VERSION):
                    center.VERSION = version
                else:
                    logging.error('Found invalid version file! The file contains %s but I\'m %s.', version, center.VERSION)

    logging.info('Running Knossos %s on %s.', center.VERSION, qt_variant)
    app = QtWidgets.QApplication([])

    res_path = get_file_path('resources.rcc')
    logging.debug('Loading resources from %s.', res_path)
    QtCore.QResource.registerResource(res_path)

    logging.debug('Loading settings...')
    load_settings()
    
    trans = QtCore.QTranslator()
    if center.settings['language']:
        lang = center.settings['language']
    else:
        lang = QtCore.QLocale()

    if trans.load(lang, 'knossos', '_', get_file_path(''), '.etak'):
        app.installTranslator(trans)
    else:
        del trans

    app.setWindowIcon(QtGui.QIcon(':/hlp.png'))
    ipc = IPCComm(center.settings_path)

    if len(sys.argv) > 1:
        if sys.argv[1] == '--install-scheme':
            from . import integration, api

            integration.init()
            api.install_scheme_handler('--silent' not in sys.argv)
            return
        elif sys.argv[1] == '--finish-update':
            updater = sys.argv[2]

            if not os.path.isfile(updater):
                logging.error('The update finished but where is the installer?! It\'s not where it\'s supposed to be! (%s)', updater)
            else:
                tries = 3
                while tries > 0:
                    try:
                        # Clean up
                        os.unlink(updater)
                    except:
                        logging.exception('Failed to remove updater! (%s)' % updater)

                    if os.path.isfile(updater):
                        time.sleep(0.3)
                        tries -= 1
                    else:
                        break

                # Delete the temporary directory.
                if os.path.basename(updater) == 'knossos_updater.exe':
                    try:
                        os.rmdir(os.path.dirname(updater))
                    except:
                        logging.exception('Failed to remove the updater\'s temporary directory.')
        else:
            tries = 3
            while tries > 0:
                if scheme_handler(sys.argv[1]):
                    break

                tries -= 1
                ipc = IPCComm(center.settings_path)

            if tries == 0:
                sys.exit(1)

            return
    elif ipc.server_exists() and scheme_handler('fso://focus'):
        return

    del ipc

    try:
        run_knossos()
    except:
        logging.exception('Uncaught exeception! Quitting...')

        # Try to tell the user
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('launcher', 'I encountered a fatal error.\nI\'m sorry but I\'m going to crash now...'))
