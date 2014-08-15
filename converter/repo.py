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

import os
import json
from collections import OrderedDict
from util import pjoin, is_archive


class RepoConf(object):
    path = None
    includes = None
    mods = None

    def __init__(self, file=None):
        self.includes = []
        self.mods = {}

        if file is not None:
            self.read(file)

    def read(self, path):
        with open(path, 'r') as stream:
            content = json.load(stream)

        self.path = path

        if '#include' in content:
            self.includes = content['#include']
            del content['#include']

        self.mods = content

    def write(self, path=None, pretty=False):
        if path is None:
            if self.path is None:
                raise Exception('Expected a path since we didn\'t open a file.')

            path = self.path

        content = self.mods.copy()
        content['#include'] = self.includes

        with open(path, 'w') as stream:
            if pretty:
                keys = list(content.keys())
                keys.sort()
                
                s_content = OrderedDict()
                for key in keys:
                    s_content[key] = content[key]

                json.dump(s_content, stream, indent=4)
            else:
                json.dump(content, stream, separators=(',', ':'))

    def parse_includes(self):
        base = os.path.dirname(self.path)
        for inc in self.includes:
            conf = RepoConf(os.path.join(base, inc))
            conf.parse_includes()

            self.mods.update(conf.mods)

    def import_tree(self, mod_tree):
        mod_tree = self._flatten_tree(mod_tree)

        for path, mod in mod_tree.items():
            # First we need its ID.
            # For now, I'll simply use the path with a prefix.
            
            id_ = 'FSOI#' + path
            if id_ in self.mods:
                # Let's update it but try to honour local modifications.
                submods = ['FSOI#' + smod.path for smod in mod.submods]
                dependencies = ['FSOI#' + path for path in mod.dependencies]
                delete = [pjoin(mod.folder, path) for path in mod.delete]

                entry = self.mods[id_]
                for smod in submods:
                    if smod not in entry['submods']:
                        entry['submods'].append(smod)
                
                for path in dependencies:
                    if path not in entry['dependencies']:
                        entry['dependencies'].append(path)
                
                for path in delete:
                    if path not in entry['delete']:
                        entry['delete'].append(path)
            else:
                # NOTE: I'm deliberatly dropping support for COPY and RENAME here.

                self.mods[id_] = {
                    'title': mod.name,
                    'version': mod.version,
                    'description': mod.desc,
                    'logo': None,
                    'notes': mod.note,
                    'submods': ['FSOI#' + smod.path for smod in mod.submods],
                    'dependencies': ['FSOI#' + path for path in mod.dependencies],
                    'source': '#FSOI',
                    'files': [],
                    'delete': [pjoin(mod.folder, path) for path in mod.delete],
                    'requirements': []
                }

            # Always keep the files in sync.
            flist = self.mods[id_]['files'] = []

            for urls, filenames in mod.urls:
                files = {}
                flist.append((urls, files))

                for name in filenames:
                    files[name] = {
                        'is_archive': is_archive(name),
                        'dest': mod.folder
                    }

    def _flatten_tree(self, mod_tree, path=None):
        if path is None:
            path = []

        result = {}
        for mod in mod_tree:
            path.append(mod.name)

            mod.path = '.'.join(path)
            result[mod.path] = mod
            result.update(self._flatten_tree(mod.submods, path))

            path.pop()

        return result
