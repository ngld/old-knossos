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

import os
import sys
import json
from . import uhf
uhf(__name__)

from .qt import QtCore # noqa

# The version should follow the http://semver.org guidelines.
# Only remove the -dev tag if you're making a release!
VERSION = '0.14.2-dev'
UPDATE_LINK = 'https://fsnebula.org/knossos'
INNOEXTRACT_LINK = 'https://fsnebula.org/storage/knossos/innoextract.json'
DEBUG = os.getenv('KN_DEBUG', '0').strip() == '1'
SENTRY_DSN = 'https://77179552b41946488346a9a2d2669d74:f7b896367bd94f0ea960b8f0ee8b7a88@sentry.gruenprint.de/9?timeout=5'

API = 'https://api.fsnebula.org/api/1/'
WEB = 'https://fsnebula.org/'
REPOS = [
    'https://cf.fsnebula.org/storage/repo.json',
    'https://fsnebula.org/storage/repo.json',
    'https://porphyrion.feralhosting.com/datacorder/nebula/repo.json'
]

LANGUAGES = {
    'en': 'English'
}

app = None
main_win = None
fs2_watcher = None
pmaster = None
auto_fetcher = None
mods = None
installed = None
fso_flags = None
has_retail = None
raven = None
raven_handler = None
sort_type = 'alphabetical'

settings = {
    'fs2_bin': None,
    'fred_bin': None,
    'base_path': None,
    'base_dirs': [],
    'custom_bar': True,
    'hash_cache': None,
    'max_downloads': 3,
    'download_bandwidth': -1.0,  # negative numbers are used to specify no limit
    'repos_override': [],
    'api_override': None,
    'web_override': None,
    'update_notify': True,
    'use_raven': True,
    'sdl2_path': None,
    'openal_path': None,
    'language': None,
    'neb_user': '',
    'neb_password': '',
    'engine_stability': 'stable',
    'fso_flags': {},
    'joystick': {
        'guid': None,
        'id': 99999
    },
    'show_fs2_mods_without_retail': False,
    'debug_log': False,
    'show_fso_builds': False
}

if sys.platform.startswith('win'):
    settings_path = os.path.expandvars('$APPDATA/knossos')
elif 'XDG_CONFIG_HOME' in os.environ or sys.platform.startswith('linux'):
    config_home = os.environ.get('XDG_CONFIG_HOME', '')

    if config_home == '':
        # As specified by the XDG Base Directory Specification this should be the default
        config_home = os.path.expandvars('$HOME/.config')

    settings_path = os.path.join(config_home, 'knossos')
    old_path = os.path.expandvars('$HOME/.knossos')

    if not os.path.isdir(settings_path) and os.path.isdir(old_path):
        settings_path = old_path

    del old_path, config_home
elif sys.platform == 'darwin':
    old_path = os.path.expandvars('$HOME/.knossos')
    settings_path = os.path.expandvars('$HOME/Library/Preferences/knossos')

    if not os.path.isdir(settings_path) and os.path.isdir(old_path):
        settings_path = old_path

    del old_path
else:
    settings_path = os.path.expanduser('~/.knossos')


class _SignalContainer(QtCore.QObject):
    update_avail = QtCore.Signal('QVariant')
    task_launched = QtCore.Signal(QtCore.QObject)


signals = _SignalContainer()

def get_library_json_name():
    return 'kn_library.json'

def save_settings():
    settings['hash_cache'] = dict()

    # Other threads might be using the hash cache. Make a local copy to avoid problems.
    for path, info in list(util.HASH_CACHE.items()):
        # Skip deleted files
        if os.path.exists(path):
            settings['hash_cache'][path] = info

    with open(os.path.join(settings_path, 'settings.json'), 'w', errors='replace') as stream:
        json.dump(settings, stream)


from . import util # noqa
