#!/usr/bin/python
## Copyright 2014 ngld <ngld@tproxy.de>
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

if six.PY2:
    import lib.py2_compat


from lib.qt import QtGui
from lib.ipc import IPCComm


app = None
ipc = None
settings_path = os.path.expanduser('~/.fs2mod-py')

if sys.platform.startswith('win'):
    settings_path = os.path.expandvars('$APPDATA/fs2mod-py')


def handle_error():
    global app, ipc
    # TODO: Try again?

    QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Failed to connect to main process!')
    if ipc is not None:
        ipc.clean()

    app.quit()


def launch_cmd(args=[]):
    if hasattr(sys, 'frozen') and sys.frozen == 1:
        my_path = [os.path.abspath(sys.executable)]
    else:
        my_path = [os.path.abspath(sys.executable), os.path.abspath(__file__)]

    return my_path + args


def scheme_handler(link):
    global app, ipc

    if hasattr(sys, 'frozen'):
        if hasattr(sys, '_MEIPASS'):
            os.chdir(sys._MEIPASS)
        else:
            os.chdir(os.path.dirname(sys.executable))
    else:
        my_path = os.path.dirname(__file__)
        if my_path != '':
            os.chdir(my_path)
    
    if not os.path.isdir(settings_path):
        os.makedirs(settings_path)
    
    if sys.platform.startswith('win'):
        # Windows won't display a console so write our log messages to a file.
        handler = logging.FileHandler(os.path.join(settings_path, 'log.txt'), 'w')
        handler.setFormatter(logging.Formatter('%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s'))
        logging.getLogger().addHandler(handler)
    
    app = QtGui.QApplication([])
    
    if not link.startswith(('fs2://', 'fso://')):
        # NOTE: fs2:// is deprecated, we don't tell anyone about it.
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'I don\'t know how to handle "%s"! I only know fso:// .' % (link))
        app.quit()
        return
    
    link = urlparse.unquote(link).split('/')
    
    if len(link) < 3:
        QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Not enough arguments!')
        app.quit()
        return
    
    if not ipc.server_exists():
        # Launch the program.
        subprocess.Popen(launch_cmd())

        # Wait for the program...
        start = time.time()
        while not ipc.server_exists():
            if time.time() - start > 20:
                # That's too long!
                QtGui.QMessageBox.critical(None, 'fs2mod-py', 'Failed to start server!')
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
    from third_party import cpuinfo

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


if __name__ == '__main__':
    ipc = IPCComm(settings_path)

    if len(sys.argv) > 1:
        if sys.argv[1] == '--cpuinfo':
            get_cpu_info()
        else:
            scheme_handler(sys.argv[1])
    elif ipc.server_exists():
        scheme_handler('fso://focus')
    else:
        del ipc

        from manager import main
        main()
