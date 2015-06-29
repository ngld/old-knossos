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

import os
import json
import re
import logging
import semantic_version

from knossos.util import pjoin, merge_dicts
from . import vfs


class RepoConf(object):
    path = None
    includes = None
    remote_includes = None
    mods = None
    meta = None
    _valid = True

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
        
        if 'mods' not in content:
            if 'id' in content and 'title' in content and 'packages' in content:
                content = {'mods': [content]}
            else:
                self._valid = False
                logging.error('I can\'t find the "mods" key.')
                return

        mods = content['mods']
        self.mods = {}

        for mod in mods:
            mod = Mod(mod)
            if mod.validate():
                if mod.mid not in self.mods:
                    self.mods[mod.mid] = {}

                self.mods[mod.mid][mod.version] = mod
            else:
                self._valid = False

    def validate(self):
        if not self._valid:
            return False

        for mvs in self.mods.values():
            for mod in mvs.values():
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
            'mods': []
        }

        for mvs in self.mods.values():
            for mod in mvs.values():
                content['mods'].append(mod.get())

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
    cmdline = ''
    submods = None
    actions = None
    packages = None

    _fields = ('id', 'title', 'version', 'folder', 'cmdline', 'logo', 'description', 'notes', 'submods', 'actions', 'packages')
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
        self.folder = values.get('folder', self.mid).strip('/')  # make sure we have a relative path
        self.cmdline = values.get('cmdline', '')
        self.logo = values.get('logo', None)
        self.description = values.get('description', '')
        self.notes = values.get('notes', '')
        self.submods = values.get('submods', [])
        self.packages = [Package(pkg, self) for pkg in values.get('packages', [])]
        self.actions = values.get('actions', [])

        try:
            self.version = semantic_version.Version(values['version'], partial=True)
        except ValueError as exc:
            logging.error('Failed to parse version for Mod "%s"! (%s)', self.title, str(exc))
            self._valid = False
            return

        # Enforce relative paths
        for act in self.actions:
            if 'glob' not in act:
                act['glob'] = True

            if 'paths' not in act:
                logging.error('An action for mod "%s" is missing its paths!', self.title)
                self._valid = False
            elif not isinstance(act['paths'], list):
                logging.error('An action for mod "%s" has an invalid type for its paths!', self.title)
                self._valid = False
            else:
                act['paths'] = [p.lstrip('/') for p in act['paths']]

            if 'type' not in act:
                logging.error('An action for mod "%s" is missing its type!', self.title)
                self._valid = False
            elif act['type'] == 'delete':
                pass
            elif act['type'] == 'move':
                if 'dest' not in act:
                    logging.error('A move action for mod "%s" is missing its dest property!', self.title)
                    self._valid = False
            elif act['type'] == 'copy':
                if 'dest' not in act:
                    logging.error('A copy action for mod "%s" is missing its dest property!', self.title)
                    self._valid = False
            elif act['type'] == 'mkdir':
                pass
            else:
                logging.error('The action type "%s" for mod "%s" is unknown!', act['type'], self.title)
                self._valid = False
                continue
            
            if 'dest' in act:
                act['dest'] = act['dest'].lstrip('/')

    def get(self):
        return {
            'id': self.mid,
            'title': self.title,
            'version': str(self.version),
            'folder': self.folder,
            'cmdline': self.cmdline,
            'logo': self.logo,
            'description': self.description,
            'notes': self.notes,
            'submods': self.submods,
            'actions': self.actions,
            'packages': [pkg.get() for pkg in self.packages]
        }

    def copy(self):
        return Mod(self.get(), self._repo)

    def validate(self):
        if not self._valid:
            return False

        for pkg in self.packages:
            if not pkg.validate():
                return False

        return True

    def build_file_list(self):
        fs = vfs.Container()
        pkg_filelist = {}

        for pkg in self.packages:
            pkg_filelist[pkg.name] = pkg.filelist = []
            for _file in pkg.files.values():
                if _file.is_archive:
                    for name, csum in _file.contents.items():
                        my_path = os.path.join(_file.dest, name)
                        fs.makedirs(os.path.dirname(my_path))
                        fs.put_file(my_path, (pkg.name, _file.filename, name, csum))
                else:
                    my_path = os.path.join(_file.dest, _file.filename)
                    fs.makedirs(os.path.dirname(my_path))
                    fs.put_file(my_path, (pkg.name, _file.filename, None, _file.md5sum))

        self.apply_actions(fs)
        filelist = fs.get_tree()
        
        for name, item in filelist.items():
            pkg_filelist[item[0]].append({
                'filename': name,
                'archive': item[1],
                'orig_name': item[2],
                'md5sum': item[3]
            })

    def apply_actions(self, fs):
        for act in self.actions:
            if act.get('glob', False):
                paths = []
                for p in act['paths']:
                    paths.extend(fs.iglob(p))
            else:
                paths = act['paths']

            if act['type'] == 'delete':
                for item in paths:
                    fs.rmtree(item)
            elif act['type'] == 'move':
                for item in paths:
                    fs.move(item, act['dest'])
            elif act['type'] == 'copy':
                for item in paths:
                    fs.copytree(item, act['dest'])
            elif act['type'] == 'mkdir':
                for item in paths:
                    fs.makedirs(item)

    def get_submods(self):
        return [self._repo.query(mid) for mid in self.submods]

    def get_files(self):
        files = {}
        for pkg in self.packages:
            files.update(pkg.get_files())

        return files


class Package(object):
    _mod = None
    _valid = True
    name = ''
    notes = ''
    status = 'recommended'
    dependencies = None
    environment = None
    files = None
    filelist = None
    executables = None

    _fields = ('name', 'notes', 'status', 'dependencies', 'environment', 'files', 'filelist', 'executables')

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
        self.filelist = values.get('filelist', [])
        self.executables = values.get('executables', [])

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
            else:
                if re.match('\d.*', dep['version']):
                    # Make a spec out of this version
                    dep['version'] = '==' + dep['version']

                try:
                    semantic_version.Spec(dep['version'])
                except ValueError as exc:
                    logging.error('Failed to parse version for one of package "%s"\'s dependencies! (%s)', self.name, str(exc))
                    self._valid = False
                    return

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
            elif 'not' not in env:
                env['not'] = False
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
        self.set_files(_files)
        mid = self._mod.mid

        if mid == '':
            raise Exception('Package "%s" initialized with Mod %s which has no ID!' % (self.name, self._mod.title))

    def set_files(self, files):
        self.files = {}

        if not isinstance(files, list):
            logging.error('"%s"\'s file list has an unknown type.', self.name)
            return False
        elif len(files) > 0 and isinstance(files[0], dict):
            for item in files:
                self.files[item['filename']] = PkgFile(item, self)
        else:
            for urls, file_items in files:
                for name, info in file_items.items():
                    info = info.copy()
                    info['filename'] = name
                    info['urls'] = [pjoin(url, name) for url in urls]
                    self.files[name] = PkgFile(info, self)

    def get(self):
        return {
            'name': self.name,
            'notes': self.notes,
            'status': self.status,
            'dependencies': self.dependencies,
            'environment': self.environment,
            'files': [f.get() for f in self.files.values()],
            'filelist': self.filelist,
            'executables': self.executables
        }

    def copy(self):
        return Package(self.get(), self._mod)

    def validate(self):
        if not self._valid:
            return False

        for f in self.files.values():
            if not f.validate():
                return False

        return True

    def get_mod(self):
        return self._mod


class PkgFile(object):
    _package = None
    _valid = True
    filename = ''
    is_archive = True
    dest = ''
    urls = None
    contents = None
    md5sum = ''
    filesize = 0

    _fields = ('filename', 'is_archive', 'dest', 'urls', 'contents', 'md5sum', 'filesize')
    _req = ('filename', 'urls')

    def __init__(self, values, package):
        super(PkgFile, self).__init__()

        self._package = package
        self.contents = {}
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
        self.dest = values.get('dest', '').strip('/')  # make sure this is a relative path
        self.urls = values['urls']
        self.contents = values.get('contents', {})
        self.md5sum = values.get('md5sum', '')
        self.filesize = values.get('filesize', 0)

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
            'urls': self.urls,
            #'contents': self.contents,
            'md5sum': self.md5sum,
            'filesize': self.filesize
        }

    def copy(self):
        return PkgFile(self.get(), self._package)

    def validate(self):
        return self._valid

    def get_files(self):
        return self.contents.keys()
