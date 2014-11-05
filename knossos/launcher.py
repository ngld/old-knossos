## Copyright 2014 Knossos authors, see NOTICE file
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
import six
from six.moves.urllib import parse as urlparse

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')

from . import center

# Initialize the FileHandler early to capture all log messages.
if not os.path.isdir(center.settings_path):
    os.makedirs(center.settings_path)

if sys.platform.startswith('win'):
    # Windows won't display a console. Let's write our log messages to a file.
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

if six.PY2:
    from . import py2_compat

from .qt import QtCore, QtGui
from .ipc import IPCComm
from . import util


app = None
ipc = None


def handle_error():
    global app, ipc
    # TODO: Try again?

    QtGui.QMessageBox.critical(None, 'Knossos', 'Failed to connect to main process!')
    if ipc is not None:
        ipc.clean()

    app.quit()


def get_cmd(args=[]):
    if hasattr(sys, 'frozen') and sys.frozen == 1:
        my_path = [os.path.abspath(sys.executable)]
    else:
        my_path = os.path.realpath(os.path.abspath(__file__))
        my_path = [os.path.abspath(sys.executable), os.path.join(os.path.dirname(my_path), '__main__.py')]

    return my_path + args


def get_file_path(name):
    my_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
    data_path = os.path.join(my_path, 'data')
    if os.path.isdir(data_path):
        return os.path.join(data_path, name)
    else:
        from pkg_resources import resource_filename
        return resource_filename(__package__, name)


def run_knossos():
    global app

    import pickle

    from . import repo, progress, integration, api
    from .windows import NebulaWindow, MainWindow, HellWindow

    # Try to load our settings.
    spath = os.path.join(center.settings_path, 'settings.pick')
    settings = center.settings
    if os.path.exists(spath):
        defaults = settings.copy()
        
        try:
            with open(spath, 'rb') as stream:
                if six.PY3:
                    settings.update(pickle.load(stream, encoding='utf8', errors='replace'))
                else:
                    settings.update(pickle.load(stream))
        except:
            logging.exception('Failed to load settings from "%s"!', spath)
        
        # Migration
        if 's_version' not in settings or settings['s_version'] < 2:
            settings['repos'] = defaults['repos']
            settings['s_version'] = 2
        
        del defaults
    else:
        # Most recent settings version
        settings['s_version'] = 2
    
    if settings['hash_cache'] is not None:
        util.HASH_CACHE = settings['hash_cache']

    util.DL_POOL.set_capacity(settings['max_downloads'])

    logging.debug('Loading resources from %s.', get_file_path('resources.rcc'))
    QtCore.QResource.registerResource(get_file_path('resources.rcc'))

    center.app = app
    center.installed = repo.InstalledRepo(settings.get('installed_mods', []))
    center.pmaster = progress.Master()
    center.pmaster.start_workers(10)

    app.setWindowIcon(QtGui.QIcon(':/hlp.png'))

    if not util.test_7z():
        QtGui.QMessageBox.critical(None, 'Error', 'I can\'t find "7z"! Please install it and run this program again.', QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
        return

    if settings['ui_mode'] == 'hell':
        center.main_win = HellWindow()
    elif settings['ui_mode'] == 'nebula':
        center.main_win = NebulaWindow()
    else:
        center.main_win = MainWindow()

    integration.init()
    QtCore.QTimer.singleShot(1, api.init_self)

    center.main_win.open()
    app.exec_()
    
    api.save_settings()
    api.shutdown_ipc()


def scheme_handler(link):
    global app, ipc

    if not link.startswith(('fs2://', 'fso://')):
        # NOTE: fs2:// is deprecated, we don't tell anyone about it.
        QtGui.QMessageBox.critical(None, 'Knossos', 'I don\'t know how to handle "%s"! I only know fso:// .' % (link))
        app.quit()
        return
    
    link = urlparse.unquote(link.strip()).split('/')
    
    if len(link) < 3:
        QtGui.QMessageBox.critical(None, 'Knossos', 'Not enough arguments!')
        app.quit()
        return
    
    if not ipc.server_exists():
        # Launch the program.
        subprocess.Popen(get_cmd())

        # Wait for the program...
        start = time.time()
        while not ipc.server_exists():
            if time.time() - start > 20:
                # That's too long!
                QtGui.QMessageBox.critical(None, 'Knossos', 'Failed to start server!')
                app.quit()
                return

            time.sleep(0.3)

    try:
        ipc.open_connection(handle_error)
    except:
        logging.exception('Failed to connect to myself!')
        handle_error()
        return

    ipc.send_message(json.dumps(link[2:]))
    ipc.close(True)
    app.quit()
    return


def get_cpu_info():
    from .third_party import cpuinfo

    info = None

    try:
        # Try querying the CPU cpuid register
        if not info and '--safe' not in sys.argv:
            info = cpuinfo.get_cpu_info_from_cpuid()

        # Try the Windows registry
        if not info:
            info = cpuinfo.get_cpu_info_from_registry()

        # Try /proc/cpuinfo
        if not info:
            info = cpuinfo.get_cpu_info_from_proc_cpuinfo()

        # Try sysctl
        if not info:
            info = cpuinfo.get_cpu_info_from_sysctl()

        # Try solaris
        if not info:
            info = cpuinfo.get_cpu_info_from_solaris()

        # Try dmesg
        if not info:
            info = cpuinfo.get_cpu_info_from_dmesg()
    except:
        logging.exception('Failed to retrieve CPU info.')

    print(json.dumps(info))


def init():
    if hasattr(sys, 'frozen'):
        if hasattr(sys, '_MEIPASS'):
            os.chdir(sys._MEIPASS)
        else:
            os.chdir(os.path.dirname(sys.executable))
        
        if sys.platform.startswith('win') and os.path.isfile('7z.exe'):
            util.SEVEN_PATH = os.path.abspath('7z.exe')
    else:
        if sys.platform.startswith('win') and os.path.isfile('7z.exe'):
            util.SEVEN_PATH = os.path.abspath('7z.exe')
        
        my_path = os.path.dirname(os.path.dirname(__file__))
        if my_path != '':
            os.chdir(my_path)

    if os.path.isfile('version'):
        with open('version', 'r') as data:
            version = data.read().strip()

            if version != center.VERSION:
                if version.startswith(center.VERSION):
                    center.VERSION = version
                else:
                    logging.error('Found invalid version file! The file contains %s but I\'m %s.', version, center.VERSION)

    logging.info('Running Knossos %s.', center.VERSION)
    
    app = QtGui.QApplication([])
    return app


def main():
    global ipc, app

    app = init()
    ipc = IPCComm(center.settings_path)

    if len(sys.argv) > 1:
        if sys.argv[1] == '--cpuinfo':
            get_cpu_info()
            return
        elif sys.argv[1] == '--install-scheme':
            from . import api
            
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
            scheme_handler(sys.argv[1])
            return
    elif ipc.server_exists():
        scheme_handler('fso://focus')
        return
    
    del ipc

    try:
        run_knossos()
    except:
        logging.exception('Uncaught exeception! Quitting...')

        # Try to tell the user
        QtGui.QMessageBox.critical(None, 'Knossos', 'I encountered a fatal error.\nI\'m sorry but I\'m going to crash now...')
