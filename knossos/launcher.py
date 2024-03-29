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
import ssl
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

from . import uhf
uhf(__name__)
from . import center

# Initialize the FileHandler early to capture all log messages.
if not os.path.isdir(center.settings_path):
    os.makedirs(center.settings_path)

# We truncate the log file on every start to avoid filling the user's disk with useless data.
log_path = os.path.join(center.settings_path, 'log.txt')

try:
    if os.path.isfile(log_path):
        os.unlink(log_path)
except Exception:
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
    from . import py2_compat  # noqa

from .qt import QtCore, QtGui, QtWidgets, variant as qt_variant
from . import util, ipc, auto_fetch


app = None
ipc_conn = None
translate = QtCore.QCoreApplication.translate


def my_excepthook(type, value, tb):
    try:
        # NOTE: This can fail (for some reason) in traceback.print_exception.
        logging.error('UNCAUGHT EXCEPTION!', exc_info=(type, value, tb))
    except Exception:
        logging.error('UNCAUGHT EXCEPTION!\n%s%s: %s' % (''.join(traceback.format_tb(tb)), type.__name__, value))

    msg = translate('launcher', 'A critical error occurred! Knossos might not work correctly until you restart it.')
    if center.raven:
        msg += '\n' + translate('launcher', 'The error has been reported and will hopefully be fixed soon.')

    msg += '\n' + translate('launcher', 'If you want to help, report this bug on our Discord channel, ' +
        'in the HLP thread or on GitHub. Just click a button below to open the relevant page.')

    try:
        box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Knossos', msg, QtWidgets.QMessageBox.Ok)

        discord = box.addButton('Open Discord', QtWidgets.QMessageBox.ActionRole)
        hlp = box.addButton('Open HLP Thread', QtWidgets.QMessageBox.ActionRole)
        github = box.addButton('Open GitHub Issues', QtWidgets.QMessageBox.ActionRole)

        box.exec_()
        choice = box.clickedButton()

        url = None
        if choice == discord:
            url = 'https://discord.gg/qfReB8t'
        elif choice == hlp:
            url = 'https://www.hard-light.net/forums/index.php?topic=94068.0'
        elif choice == github:
            url = 'https://github.com/ngld/knossos/issues'

        if url:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
    except Exception:
        pass


def get_cmd(args=[]):
    if hasattr(sys, 'frozen'):
        my_path = [os.path.abspath(sys.executable)]
    else:
        my_path = [os.path.abspath(sys.executable), os.path.abspath('__main__.py')]

    return my_path + args


def get_file_path(name):
    if hasattr(sys, 'frozen') or os.path.isdir('data'):
        return os.path.join('data', name)
    else:
        from pkg_resources import resource_filename
        return resource_filename(__package__, name)


def load_settings():
    spath = os.path.join(center.settings_path, 'settings.json')
    settings = center.settings
    if os.path.exists(spath):
        try:
            with open(spath, 'r') as stream:
                settings.update(json.load(stream))
        except Exception:
            logging.exception('Failed to load settings from "%s"!', spath)

        # Migration
        if 's_version' not in settings:
            settings['s_version'] = 0

        if settings['s_version'] < 6:
            for name in ('mods', 'installed_mods', 'repos', 'nebula_link', 'nebula_web'):
                if name in settings:
                    del settings[name]

            settings['s_version'] = 6
    else:
        # Most recent settings version
        settings['s_version'] = 6

    if settings['hash_cache'] is not None:
        util.HASH_CACHE = settings['hash_cache']

    if settings['use_raven']:
        util.enable_raven()

    if settings['repos_override']:
        center.REPOS = settings['repos_override']

    if settings['api_override']:
        center.API = settings['api_override']

    if settings['web_override']:
        center.WEB = settings['web_override']

    if settings['debug_log']:
        logging.getLogger().setLevel(logging.DEBUG)

    util.ensure_tempdir()
    return settings


def run_knossos():
    global app

    from .windows import HellWindow

    center.app = app
    center.main_win = HellWindow()
    app.processEvents()

    if sys.platform.startswith('win') and os.path.isfile('7z.exe'):
        util.SEVEN_PATH = os.path.abspath('7z.exe')
    elif sys.platform == 'darwin' and os.path.isfile('7z'):
        util.SEVEN_PATH = os.path.abspath('7z')

    translate = QtCore.QCoreApplication.translate

    if not util.test_7z():
        QtWidgets.QMessageBox.critical(None, 'Knossos', translate(
            'launcher', 'I can\'t find "7z"! Please install it and run this program again.'))
        return

    util.DL_POOL.set_capacity(center.settings['max_downloads'])
    if center.settings['download_bandwidth'] > 0.0:
        util.SPEED_LIMIT_BUCKET.set_rate(center.settings['download_bandwidth'])

    from . import repo, progress, integration

    center.installed = repo.InstalledRepo()
    center.pmaster = progress.Master()
    center.pmaster.start_workers(10)
    center.mods = repo.Repo()
    center.auto_fetcher = auto_fetch.AutoFetcher(center.settings['fetch_interval'])

    # This has to run before we can load any mods!
    repo.CPU_INFO = util.get_cpuinfo()

    integration.init()

    # Init SDL at the start to load up video modes, which only works
    # on the main thread with some OSes (macOS in particular)
    from knossos import clibs
    clibs.init_sdl()

    center.main_win.start_init()

    app.exec_()

    center.save_settings()
    ipc.shutdown()


def handle_ipc_error():
    global app, ipc_conn

    logging.warning('Failed to connect to main process!')

    if ipc_conn is not None:
        ipc_conn.clean()
        ipc_conn = None


def scheme_handler(link):
    global app, ipc_conn

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

    if not ipc_conn.server_exists():
        # Launch the program.
        subprocess.Popen(get_cmd())

        # Wait for the program...
        start = time.time()
        while not ipc_conn.server_exists():
            if time.time() - start > 20:
                # That's too long!
                QtWidgets.QMessageBox.critical(None, 'Knossos', translate('launcher', 'Failed to start server!'))
                app.quit()
                return True

            time.sleep(0.3)

    try:
        ipc_conn.open_connection(handle_ipc_error)
    except Exception:
        logging.exception('Failed to connect to myself!')
        handle_ipc_error()
        return False

    if not ipc_conn:
        return False

    ipc_conn.send_message(json.dumps(link[2:]))
    ipc_conn.close(True)
    app.quit()
    return True


def main():
    global ipc_conn, app

    # Default to replacing errors when de/encoding.
    import codecs

    codecs.register_error('strict', codecs.replace_errors)
    codecs.register_error('really_strict', codecs.strict_errors)

    sys.excepthook = my_excepthook

    # The version file is only read in dev builds.
    if center.VERSION.endswith('-dev'):
        if 'KN_VERSION' in os.environ:
            center.VERSION = os.environ['KN_VERSION'].strip()
        else:
            try:
                with open('../.git/HEAD') as stream:
                    ref = stream.read().strip().split(':')
                    assert ref[0] == 'ref'

                with open('../.git/' + ref[1].strip()) as stream:
                    center.VERSION += '+' + stream.read()[:7]
            except Exception:
                pass

    logging.info('Running Knossos %s on %s and Python %s.', center.VERSION, qt_variant, sys.version)
    logging.info('OpenSSL version: %s', ssl.OPENSSL_VERSION)

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

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
    ipc_conn = ipc.IPCComm(center.settings_path)

    if len(sys.argv) > 1:
        if sys.argv[1] == '--finish-update':
            updater = sys.argv[2]

            if not os.path.isfile(updater):
                logging.error('The update finished but where is the installer?! It\'s not where it\'s supposed to be! (%s)', updater)
            else:
                tries = 3
                while tries > 0:
                    try:
                        # Clean up
                        os.unlink(updater)
                    except Exception:
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
                    except Exception:
                        logging.exception('Failed to remove the updater\'s temporary directory.')
        elif sys.argv[1].startswith('-psn_'):
            # This parameter is automatically passed by Finder on macOS, ignore it.
            pass
        else:
            tries = 3
            while tries > 0:
                if scheme_handler(sys.argv[1]):
                    break

                tries -= 1
                ipc_conn = ipc.IPCComm(center.settings_path)

            if tries == 0:
                sys.exit(1)

            return
    elif ipc_conn.server_exists() and scheme_handler('fso://focus'):
        return

    del ipc_conn

    try:
        run_knossos()
    except Exception:
        logging.exception('Uncaught exeception! Quitting...')

        # Try to tell the user
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            translate('launcher', 'I encountered a fatal error.\nI\'m sorry but I\'m going to crash now...'))
