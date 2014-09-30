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
import semantic_version
import logging

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
            self.mods[mod['id']] = Mod(mod)

    def validate(self):
        for mod in self.mods.values():
            if not mod.validate():
                return False

        return True

    def write(self, path=None, pretty=False):
        if path is None:
            if self.path is None:
                raise Exception('Expected a path since we didn\'t open a file.')

            path = self.path

        content = {
            'includes': self.includes,
            'remote_includes': self.remote_includes,
            'mods': [mod.get() for mod in self.mods]
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


class Mod(object):
    _repo = None
    _valid = True
    mid = ''
    title = ''
    version = None
    folder = None
    logo = ''
    description = ''
    notes = ''
    submods = None
    actions = None
    packages = None

    _fields = ('id', 'title', 'version', 'folder', 'logo', 'description', 'notes', 'submods', 'actions', 'packages')
    _req = ('id', 'title', 'version')

    def __init__(self, values=None, repo=None):
        self.actions = []
        self.packages = []

        if repo is not None:
            self._repo = self

        if values is not None:
            self.set(values)

    def set(self, values):
        title = values.get('title', values.get('id', 'Unknown'))

        tm_keys = set(values.keys()) - set(self._fields)
        for name in tm_keys:
            logging.warning('Ignored unknown option "%s" set for mod "%s"!', name, title)

        for name in self._req:
            if name not in values:
                logging.error('Missing option "%s" for mod "%s"!', name, title)
                self._valid = False

        if not self._valid:
            return

        self.mid = values['id']
        self.title = values['title']
        self.version = semantic_version.Version(values['version'], partial=True)
        self.folder = values.get('folder', '').strip('/')  # make sure we have a relative path
        self.logo = values.get('logo', None)
        self.description = values.get('description', '')
        self.notes = values.get('notes', '')
        self.submods = values.get('submods', [])
        self.actions = values.get('actions', [])

        self.packages = []
        for pkg in values.get('packages', []):
            pkg = Package(pkg, self)
            if pkg.check_env():
                self.packages.append(pkg)

        # Enforce relative paths
        for act in self.actions:
            if 'type' not in act:
                logging.error('An action for mod "%s" is missing its type!', self.title)
                self._valid = False
            elif act['type'] == 'delete':
                if 'paths' not in act:
                    logging.error('A delete action for mod "%s" is missing its paths!', self.title)
                    self._valid = False
                elif not isinstance(act['type'], list):
                    logging.error('A delete action for mod "%s" has an invalid type for its paths!', self.title)
                    self._valid = False

                if 'glob' not in act:
                    act['glob'] = False
            elif act['type'] == 'move':
                if 'paths' not in act:
                    logging.error('A move action for mod "%s" is missing its paths!', self.title)
                    self._valid = False
                elif not isinstance(act['type'], list):
                    logging.error('A move action for mod "%s" has an invalid type for its paths!', self.title)
                    self._valid = False

                if 'dest' not in act:
                    logging.error('A move action for mod "%s" is missing its dest property!', self.title)
                    self._valid = False

                if 'glob' not in act:
                    act['glob'] = False
            else:
                logging.error('The action type "%s" for mod "%s" is unknown!', act['type'], self.title)
                self._valid = False
                continue
            
            if 'paths' in act:
                act['paths'] = [p.lstrip('/') for p in act['paths']]

            if 'dest' in act:
                act['dest'] = act['dest'].lstrip('/')

    def get(self):
        return {
            'id': self.mid,
            'title': self.title,
            'version': str(self.version),
            'folder': self.folder,
            'logo': self.logo,
            'description': self.description,
            'notes': self.notes,
            'submods': self.submods,
            'actions': self.actions,
            'packages': [pkg.get() for pkg in self.packages]
        }

    def validate(self):
        if not self._valid:
            return False

        for pkg in self.packages:
            if not pkg.validate():
                return False

        return True

    def get_submods(self):
        return [self._repo.query(mid) for mid in self.submods]

    def get_files(self):
        files = {}
        for pkg in self.packages:
            files.update(pkg.get_files())

        return files


class Package(object):
    _mod = None
    _valid = False
    name = ''
    notes = ''
    status = 'recommended'
    dependencies = None
    environment = None
    files = None

    _fields = ('name', 'notes', 'status', 'dependencies', 'environment', 'files')

    def __init__(self, values=None, mod=None):
        self._mod = mod
        self.dependencies = []
        self.environment = []
        self.files = []

        if values is not None:
            self.set(values)

    def set(self, values):
        if 'name' not in values:
            logging.error('Missing the name for one of "%s"\'s packages!', self._mod.title)
            self._valid = False
            return

        for name in values:
            if name not in self._fields:
                logging.warning('Ignoring unknown option "%s" for package "%s"!', name, values['name'])

        self.name = values['name']
        self.notes = values.get('notes', '')
        self.status = values.get('status', 'recommended')
        self.dependencies = values.get('dependencies', [])
        self.environment = values.get('environment', [])
        self.files = {}

        # Validate this package's options
        if self.status not in ('required', 'recommended', 'optional'):
            logging.error('Unknown status "%s" for package "%s" (of Mod "%s")!', self.status, self.name, self._mod.title)
            self._valid = False

        for dep in self.dependencies:
            if 'id' not in dep:
                logging.error('Missing the ID for one of package "%s"\'s dependencies!', self.name)
                self._valid = False

            if 'version' not in dep:
                logging.error('Missing the version of one of package "%s"\'s dependencies!', self.name)
                self._valid = False

            for name in dep:
                if name not in ('id', 'version', 'packages'):
                    logging.warning('Ignored unknown option for "%s" dependency of package "%s"!', dep.get('id', '???'), self.name)

        for env in self.environment:
            if 'type' not in env:
                logging.error('Missing the type for one of "%s"\'s environment conditions!', self.name)
                self._valid = False
            elif 'value' not in env:
                logging.error('Missing the value for one of "%s"\'s environment conditions!', self.name)
                self._valid = False
            elif env['type'] == 'cpu_feature':
                # TODO
                pass
            elif env['type'] == 'os':
                if env['value'] not in ('windows', 'linux', 'macos'):
                    logging.error('Unknown operating system "%s" for package "%s"!', env['value'], self.name)
                    self._valid = False
            else:
                logging.error('Unknown environment condition "%s" for package "%s"!', env['type'], self.name)
                self._valid = False

        _files = values.get('files', [])

        if isinstance(_files, dict):
            self.files = _files
            for name, item in _files.items():
                item['filename'] = name
                item['dest'] = item.get('dest', '').strip('/')  # make sure this is a relative path
                self.files[item['filename']] = PkgFile(item, self)

        elif isinstance(_files, list):
            for item in _files:
                item['dest'] = item.get('dest', '').strip('/')  # make sure this is a relative path
                self.files[item['filename']] = PkgFile(item, self)
        else:
            logging.error('"%s"\'s file list has an unknown type.', self.name)
            self._valid = False
            return

        has_mod_dep = False
        mid = self._mod.mid

        if mid == '':
            raise Exception('Package "%s" initialized with Mod %s which has no ID!' % (self.name, self._mod.title))

        for info in self.dependencies:
            if info['id'] == mid:
                has_mod_dep = True
                break

        if not has_mod_dep:
            self.dependencies.append({
                'id': self.get_mod().mid,
                'version': '*',
                'packages': []
            })

    def get(self):
        return {
            'name': self.name,
            'notes': self.notes,
            'status': self.status,
            'dependencies': self.dependencies,
            'environment': self.environment,
            'files': [f.get() for f in self.files]
        }

    def validate(self):
        if not self._valid:
            return False

        for f in self.files:
            if not f.validate():
                return False

        return True

    def get_mod(self):
        return self._mod

    def get_files(self):
        files = {}
        for name, item in self.files.items():
            if item['is_archive']:
                for path, csum in item['contents'].items():
                    files[os.path.join(item['dest'], path)] = (csum, name)
            else:
                files[os.path.join(item['dest'], name)] = (item['md5sum'], name)

        return files


class PkgFile(object):
    _package = None
    _valid = True
    filename = ''
    is_archive = True
    dest = ''
    urls = None

    _fields = ('filename', 'is_archive', 'dest', 'urls')
    _req = ('filename', 'urls')

    def __init__(self, values, package):
        super(PkgFile, self).__init__()

        self._package = package
        self.set(values)

    def set(self, values):
        for name in self._req:
            if name not in values:
                logging.error('Missing option "%s" for file "%s"!', name, values.get('filename', '???'))
                self._valid = False
                return

        for name in values:
            if name not in self._fields:
                logging.warning('Ignoring unknown option "%s" for file "%s"!', name, values['filename'])

        self.filename = values['filename']
        self.is_archive = values.get('is_archive', True)
        self.dest = values.get('dest', '')
        self.urls = values['urls']

        if not isinstance(self.urls, list):
            logging.error('Unknown type for URL list for file "%s"!', self.filename)
            self._valid = False
            return

        # TODO: Check URLs ?

    def get(self):
        return {
            'filename': self.filename,
            'is_archive': self.is_archive,
            'dest': self.dest,
            'urls': self.urls
        }

    def validate(self):
        return self._valid
