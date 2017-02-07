## Copyright 2015 Knossos authors, see NOTICE file
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

import os
import sys
from .qt import QtCore

# The version should follow the http://semver.org guidelines.
# Only remove the -dev tag if you're making a release!
VERSION = '0.3.0'
UPDATE_LINK = 'https://dev.tproxy.de/knossos'
INNOEXTRACT_LINK = 'https://dev.tproxy.de/knossos/innoextract.txt'
DEBUG = os.environ.get('KN_DEBUG') == '1'
SENTRY_DSN = 'https://77179552b41946488346a9a2d2669d74:f7b896367bd94f0ea960b8f0ee8b7a88@sentry.gruenprint.de/9'

app = None
main_win = None
shared_files = {}
fs2_watcher = None
pmaster = None
mods = None
installed = None
fso_flags = None
has_retail = None
raven = None
raven_handler = None

settings = {
    'fs2_bin': None,
    'fs2_path': None,
    'pins': {},
    'cmdlines': {},
    'hash_cache': None,
    'max_downloads': 3,
    'repos': [('https://fsnebula.org/repo/master.json', 'FSNebula')],
    'nebula_link': 'https://fsnebula.org/',
    'update_channel': 'stable',
    'update_notify': True,
    'ui_mode': 'hell',
    'keyboard_layout': 'default',
    'keyboard_setxkbmap': False,
    'use_raven': True,
    'mod_settings': {}
}

if '-dev' in VERSION:
    settings['update_channel'] = 'develop'

if sys.platform.startswith('win'):
    settings_path = os.path.expandvars('$APPDATA/knossos')
elif 'XDG_CONFIG_HOME' in os.environ:
    settings_path = os.path.expandvars('$XDG_CONFIG_HOME/knossos')
else:
    settings_path = os.path.expanduser('~/.knossos')


class _SignalContainer(QtCore.QObject):
    fs2_launched = QtCore.Signal()
    fs2_failed = QtCore.Signal(int)
    fs2_quit = QtCore.Signal()
    fs2_path_changed = QtCore.Signal()
    fs2_bin_changed = QtCore.Signal()
    list_updated = QtCore.Signal()
    repo_updated = QtCore.Signal()
    update_avail = QtCore.Signal('QVariant')
    task_launched = QtCore.Signal(QtCore.QObject)


signals = _SignalContainer()
