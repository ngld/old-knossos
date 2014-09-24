## Copyright 2014 fs2mod-py authors, see NOTICE file
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
from lib.util import pjoin, is_archive, merge_dicts


class RepoConf(object):
    path = None
    includes = None
    remote_includes = None
    mods = None
    meta = None

    def __init__(self, file=None):
        self.includes = []
        self.mods = {}

        if file is not None:
            self.read(file)

    def read(self, path):
        with open(path, 'r') as stream:
            content = json.load(stream)

        self.path = path
        
        self.includes = content.get('includes', [])
        self.remote_includes = content.get('remote_includes', [])
        
        mods = content['mods']
        self.mods = {}

        for mod in mods:
            self.mods[mod['id']] = mod

    def write(self, path=None, pretty=False):
        if path is None:
            if self.path is None:
                raise Exception('Expected a path since we didn\'t open a file.')

            path = self.path

        content = {
            'includes': self.includes,
            'remote_includes': self.remote_includes,
            'mods': self.mods.values()
        }

        if pretty:
            content['mods'].sort(key=lambda i: i['id'])
        
        with open(path, 'w') as stream:
            if pretty:
                json.dump(content, stream, indent=4)
            else:
                json.dump(content, stream, separators=(',', ':'))

    def parse_includes(self):
        base = os.path.dirname(self.path)
        for inc in self.includes:
            conf = RepoConf(os.path.join(base, inc))
            conf.parse_includes()

            merge_dicts(self.mods, conf.mods)

    def import_tree(self, mod_tree):
        mod_tree = self._flatten_tree(mod_tree)

        for path, mod in mod_tree.items():
            # First we need its ID.
            # For now, I'll simply use the path with a prefix.
            
            id_ = 'FSOI#' + path
            if id_ in self.mods:
                # Let's update it but try to honour local modifications.
                submods = ['FSOI#' + '.'.join(smod.path) for smod in mod.submods]
                dependencies = ['FSOI#' + path for path in mod.dependencies]
                delete = [pjoin(mod.folder, path) for path in mod.delete]

                entry = self.mods[id_]
                for smod in submods:
                    if smod not in entry['submods']:
                        entry['submods'].append(smod)
                
                e_deps = entry['packages'][0]['dependencies']
                for path in dependencies:
                    if path not in e_deps:
                        e_deps.append(path)
                
                del_files = []
                for act in entry['actions']:
                    if act['type'] == 'delete':
                        del_files.extend(act['files'])

                missing_del_files = set(delete) - set(del_files)
                added = False
                for act in entry['actions']:
                    if act['type'] == 'delete':
                        act['files'].extend(missing_del_files)
                        added = True
                
                if not added:
                    entry['actions'].append({'type': 'delete', 'files': missing_del_files})
            else:
                # NOTE: I'm deliberatly dropping support for COPY and RENAME here.

                entry = self.mods[id_] = {
                    'id': id_,
                    'title': mod.name,
                    'version': mod.version,
                    'description': mod.desc,
                    'logo': None,
                    'notes': mod.note,
                    'submods': ['FSOI#' + '.'.join(smod.path) for smod in mod.submods],
                    'packages': [
                        {
                            'name': 'Core files',
                            'notes': '',
                            'status': 'required',
                            'dependencies': [{'id': 'FSOI#' + path, 'version': '*', 'packages': []} for path in mod.dependencies],
                            'environment': [],
                            'files': []
                        }
                    ],
                    'actions': [{
                        'type': 'delete',
                        'files': [pjoin(mod.folder, path) for path in mod.delete]
                    }]
                }

            trail = 'FSOI#'
            e_deps = entry['packages'][0]['dependencies']
            for item in mod.path:
                trail += item
                if trail not in e_deps:
                    e_deps.append({'id': trail, 'version': '*', 'packages': []})

                trail += '.'

            # Always keep the files in sync.
            flist = self.mods[id_]['packages'][0]['files'] = []

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

            mod.path = path
            result['.'.join(mod.path)] = mod
            result.update(self._flatten_tree(mod.submods, path))

            path.pop()

        return result
