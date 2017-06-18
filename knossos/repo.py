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
import json
import shutil
import hashlib
import semantic_version
import six
from datetime import datetime
from semantic_version import SpecItem

from . import uhf
uhf(__name__)

from . import center, util

# You have to fill this using https://github.com/workhorsy/py-cpuinfo .
CPU_INFO = None


class ModNotFound(Exception):
    mid = None
    spec = None

    def __init__(self, message, mid, spec=None):
        super(ModNotFound, self).__init__(message)

        self.mid = mid
        self.spec = spec


class PackageNotFound(ModNotFound):
    package = None

    def __init__(self, message, mid, package, spec=None):
        super(PackageNotFound, self).__init__(message, mid, spec)

        self.package = package


class Repo(object):
    base = None
    is_link = False
    mods = None
    includes = None
    pins = None

    def __init__(self, data=None):
        self.mods = {}
        self.pins = {}

        if data is not None:
            self.set(data)

    def empty(self):
        return len(self.mods) == 0

    def clear(self):
        self.mods = {}
        self.pins = {}

    def load_json(self, path):
        self.base = os.path.dirname(path)
        with open(path, 'r') as stream:
            self.set(json.load(stream))

    def save_json(self, path):
        with open(path, 'w') as stream:
            json.dump(self.get(), stream)

    def set(self, info):
        for m, v in info['pins'].items():
            self.pins[m] = semantic_version.Version(v)

        for mod in info['mods']:
            self.add_mod(Mod(mod, self))

    def get(self):
        mods = []
        for v in self.mods.values():
            for mod in v:
                mods.append(mod.get())

        pins = self.pins.copy()
        for m, v in pins.items():
            pins[m] = str(v)

        return {
            'pins': pins,
            'mods': mods
        }

    def fetch(self, link):
        self.base = os.path.dirname(link)
        self.is_link = True
        self.parse(util.get(link))

    def read(self, path):
        self.base = os.path.dirname(path)
        h = open(path, 'r')
        self.parse(h)
        h.close()

    def parse(self, obj):
        if not obj:
            return

        if isinstance(obj, six.string_types):
            data = json.loads(obj)
        else:
            data = json.load(obj)

        self.mods = {}
        self.includes = data.get('includes', [])

        for inc in self.includes:
            item = Repo()
            if self.is_link:
                item.fetch(util.url_join(self.base, inc))
            else:
                item.read(os.path.join(self.base, inc))

            self.merge(item)

        for mod in data.get('mods', []):
            self.add_mod(Mod(mod, self))

    def add_mod(self, mod):
        mid = mod.mid

        if len(mod.packages) == 0:
            logging.warning('Mod %s is empty, ignoring it!', mod)
            return

        if mid in self.mods:
            inserted = False

            for i, item in enumerate(self.mods[mid]):
                if item.version == mod.version:
                    if mod._repo is None:
                        mod_base = 'None'
                    else:
                        mod_base = mod._repo.base

                    logging.info('Mod "%s" (%s) from "%s" overwrites an existing mod version!', mid, mod.version, mod_base)

                    self.mods[mid][i] = mod
                    inserted = True
                    break

            if not inserted:
                self.mods[mid].append(mod)
                self.mods[mid].sort(key=lambda m: m.version, reverse=True)
        else:
            self.mods[mid] = [mod]

        mod._repo = self

    def remove_mod(self, mod):
        mid = mod.mid

        if mid not in self.mods:
            raise ModNotFound('Mod "%s" (%s) could not be removed from %s!' % (mid, mod.version, self.base))

        idx = None
        for i, item in enumerate(self.mods[mid]):
            if item.version == mod.version:
                idx = i
                break

        if not idx:
            raise ModNotFound('Mod "%s" (%s) could not be removed from %s because the exact version was missing!' % (mid, mod.version, self.base))

        del self.mods[mid][idx]

        if len(self.mods[mid]) == 0:
            del self.mods[mid]

    def merge(self, repo):
        for mvs in repo.mods.values():
            for mod in mvs:
                self.add_mod(mod)

    def pin(self, mod, version=None):
        if isinstance(mod, Package):
            mod = mod.get_mod()

        if isinstance(mod, Mod):
            version = mod.version
            mod = mod.mid

        if not isinstance(mod, str) or not isinstance(version, semantic_version.Version):
            raise ValueError('%s is not a string or %s is not a valid version!' % (mod, version))

        self.pins[mod] = version

    def unpin(self, mod):
        if isinstance(mod, Package):
            mod = mod.get_mod().mid
        elif isinstance(mod, Mod):
            mod = mod.mid

        if mod in self.pins:
            del self.pins[mod]

    def get_pin(self, mod):
        if isinstance(mod, Package):
            mod = mod.get_mod()

        if isinstance(mod, Mod):
            mod = mod.mid

        return self.pins.get(mod, None)

    def query(self, mid, spec=None, pname=None):
        if isinstance(mid, Package):
            mod = mid.get_mod()
            pname = mid.name
            mid = mod.mid
            spec = util.Spec.from_version(mod.version)

            del mod
        elif isinstance(mid, Mod):
            spec = util.Spec.from_version(mid.version)
            mid = mid.mid

        if mid not in self.mods:
            raise ModNotFound('Mod "%s" wasn\'t found!' % (mid), mid)

        if spec is None and mid in self.pins:
            spec = util.Spec.from_version(self.pins[mid])

        candidates = self.mods[mid]
        if spec is None:
            mod = candidates[0]
        else:
            if isinstance(spec, semantic_version.Version):
                logging.warning('Repo.query(): Expected Spec but got Version instead! (%s)' % repr(spec))
                spec = util.Spec.from_version(spec)

            version = spec.select([mod.version for mod in candidates])
            if not version:
                raise ModNotFound('Mod "%s" %s wasn\'t found!' % (mid, spec), mid, spec)

            for m in candidates:
                if m.version == version:
                    mod = m
                    break

        if pname is not None:
            for pkg in mod.packages:
                if pkg.name == pname:
                    return pkg

            raise ModNotFound('The package "%s" for mod "%s" wasn\'t found!' % (pname, mid), mid)
        else:
            return mod

    def query_all(self, mid, spec=None):
        if mid not in self.mods:
            raise ModNotFound('Mod "%s" wasn\'t found!' % (mid), mid)

        for mod in self.mods[mid]:
            if spec is None or spec.match(mod.version):
                yield mod

    def has(self, mid, spec=None, pname=None):
        try:
            self.query(mid, spec, pname)
            return True
        except ModNotFound:
            return False

    def get_tree(self):
        roots = set(self.mods.keys())
        return [self.mods[mid][0] for mid in roots]

    def get_list(self):
        for mod in self.mods.values():
            yield mod[0]

    # TODO: Is this overcomplicated?
    def process_pkg_selection(self, pkgs):
        dep_dict = {}
        ndeps = pkgs

        # Resolve the pkgs' dependencies
        while len(ndeps) > 0:
            _nd = ndeps
            ndeps = []

            for pkg in _nd:
                for dep, version in pkg.resolve_deps():
                    mid = dep.get_mod().mid

                    if mid not in dep_dict:
                        dep_dict[mid] = {}

                    if dep.name not in dep_dict[mid]:
                        dep_dict[mid][dep.name] = {}

                    if version not in dep_dict[mid][dep.name]:
                        dep_dict[mid][dep.name][version] = dep
                        ndeps.append(dep)

        # Check for conflicts (and try to resolve them if possible).
        dep_list = set()
        for mid, deps in dep_dict.items():
            for name, variants in deps.items():
                if len(variants) == 1:
                    dep_list.add(next(iter(variants.values())))
                else:
                    specs = variants.keys()
                    remains = []

                    for v in variants.values():
                        ok = True
                        for spec in specs:
                            if not spec.match(v.get_mod().version):
                                ok = False
                                break

                        if ok:
                            remains.append(v)

                    if len(remains) == 0:
                        v = (list(variants.values())[0].name, ','.join([str(s) for s in specs]))
                        raise PackageNotFound('No version of package "%s" found for these constraints: %s' % v, mid, list(variants.values())[0].name)
                    else:
                        # Pick the latest
                        remains.sort(key=lambda v: v.get_mod().version)
                        dep_list.add(remains[-1])

        dep_list |= set(pkgs)
        return dep_list

    def save_logos(self, path):
        for mid, mvs in self.mods.items():
            for mod in mvs:
                mod.save_logo(path)


class Mod(object):
    _repo = None
    mid = ''
    title = ''
    mtype = 'mod'
    version = None
    parent = None
    cmdline = ''
    logo = None
    logo_path = None
    tile = None
    tile_path = None
    description = ''
    notes = ''
    release_thread = None
    videos = None
    first_release = None
    last_update = None
    actions = None
    packages = None

    __fields__ = ('mid', 'title', 'type', 'version', 'parent', 'cmdline', 'logo', 'tile',
        'description', 'notes', 'actions', 'packages')

    def __init__(self, values=None, repo=None):
        self.actions = []
        self.packages = []
        self.videos = []

        if repo is not None:
            self._repo = repo

        if values is not None:
            self.set(values)

    def __repr__(self):
        return '<Mod "%s" %s (%s)>' % (self.title, self.version, self.mid)

    def set(self, values):
        self.mid = values['id']
        self.title = values['title']
        self.mtype = values.get('type', 'mod')  # Backwards compatibility
        self.version = semantic_version.Version(values['version'], partial=True)
        self.parent = values.get('parent', 'FS2')
        self.cmdline = values.get('cmdline', '')
        self.logo = values.get('logo', None)
        self.tile = values.get('tile', None)
        self.description = values.get('description', '')
        self.notes = values.get('notes', '')
        self.release_thread = values.get('release_thread', None)
        self.videos = values.get('videos', [])
        self.first_release = values.get('first_release', None)
        self.last_update = values.get('last_update', None)
        self.actions = values.get('actions', [])

        self.packages = []
        for pkg in values.get('packages', []):
            pkg = Package(pkg, self)
            if pkg.check_env():
                self.packages.append(pkg)

        if self._repo is not None and self._repo.base is not None:
            if self.logo is not None:
                if '://' in self._repo.base:
                    self.logo = util.url_join(self._repo.base, self.logo)
                else:
                    self.logo = os.path.abspath(os.path.join(self._repo.base, self.logo))

            if self.tile is not None:
                if '://' in self._repo.base:
                    self.tile = util.url_join(self._repo.base, self.tile)
                else:
                    self.tile = os.path.abspath(os.path.join(self._repo.base, self.tile))

        if self.first_release:
            self.first_release = datetime.strptime(self.first_release, '%Y-%m-%d')

        if self.last_update:
            self.last_update = datetime.strptime(self.last_update, '%Y-%m-%d')

        # Enforce relative paths
        for act in self.actions:
            if 'paths' in act:
                act['paths'] = [p.lstrip('/') for p in act['paths']]

            if 'dest' in act:
                act['dest'] = act['dest'].lstrip('/')

    def get(self):
        return {
            'id': self.mid,
            'title': self.title,
            'type': self.mtype,
            'version': str(self.version),
            'parent': self.parent,
            'cmdline': self.cmdline,
            'logo': self.logo,
            'logo_path': self.logo,
            'tile': self.tile,
            'tile_path': self.tile,
            'description': self.description,
            'notes': self.notes,
            'release_thread': self.release_thread,
            'videos': self.videos,
            'first_release': self.first_release.strftime('%Y-%m-%d') if self.first_release else None,
            'last_update': self.last_update.strftime('%Y-%m-%d') if self.last_update else None,
            'actions': self.actions,
            'packages': [pkg.get() for pkg in self.packages]
        }

    def copy(self):
        return Mod(self.get(), self._repo)

    def get_files(self):
        files = []
        for pkg in self.packages:
            for item in pkg.filelist:
                item = item.copy()
                item['package'] = pkg.name
                files.append(item)

        return files

    def resolve_deps(self, only_required=True):
        if only_required:
            pkgs = [pkg for pkg in self.packages if pkg.status == 'required']
        else:
            pkgs = [pkg for pkg in self.packages if pkg.status in ('required', 'recommended')]

        return self._repo.process_pkg_selection(pkgs)

    def save_logo(self, dest):
        if self.logo is not None:
            suffix = '.' + self.logo.split('.')[-1]
            path = os.path.join(dest, 'logo_' + hashlib.md5(self.logo.encode('utf8')).hexdigest() + suffix)

            if not os.path.isfile(path):
                if '://' in self.logo:
                    # That's a URL
                    with open(path, 'wb') as fobj:
                        util.download(self.logo, fobj)
                else:
                    shutil.copyfile(self.logo, path)

            self.logo_path = self.logo = os.path.abspath(path)

        if self.tile is not None:
            suffix = '.' + self.tile.split('.')[-1]
            path = os.path.join(dest, 'tile_' + hashlib.md5(self.tile.encode('utf8')).hexdigest() + suffix)

            if not os.path.isfile(path):
                if '://' in self.tile:
                    # That's a URL
                    with open(path, 'wb') as fobj:
                        util.download(self.tile, fobj)
                else:
                    shutil.copyfile(self.tile, path)

            self.tile_path = self.tile = os.path.abspath(path)


class Package(object):
    _mod = None
    name = ''
    notes = ''
    status = 'recommended'
    dependencies = None
    environment = None
    files = None
    filelist = None
    executables = None

    def __init__(self, values=None, mod=None):
        self._mod = mod
        self.dependencies = []
        self.environment = []
        self.files = {}

        if values is not None:
            self.set(values)

    def __repr__(self):
        return '<Package "%s" of %s>' % (self.name, self._mod)

    def set(self, values):
        self.name = values['name']
        self.notes = values.get('notes', '')
        self.status = values.get('status', 'recommended').lower()
        self.dependencies = values.get('dependencies', [])
        self.environment = values.get('environment', [])
        self.files = {}
        self.filelist = values.get('filelist', [])
        self.executables = values.get('executables', [])

        _files = values.get('files', [])

        if isinstance(_files, dict):
            self.files = _files
            for name, item in _files.items():
                item['filename'] = name
                item['dest'] = item.get('dest', '').strip('/')  # make sure this is a relative path

        elif isinstance(_files, list):
            for item in _files:
                item['dest'] = item.get('dest', '').strip('/')  # make sure this is a relative path
                self.files[item['filename']] = item
        else:
            logging.warning('"%s"\'s file list has an unknown type.', self.name)

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
                'version': '==' + str(self.get_mod().version),
                'packages': []
            })

    def get(self):
        return {
            'name': self.name,
            'notes': self.notes,
            'status': self.status,
            'dependencies': self.dependencies,
            'environment': self.environment,
            'files': list(self.files.values()),
            'filelist': self.filelist,
            'executables': self.executables
        }

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

    def resolve_deps(self):
        result = []
        for dep in self.dependencies:
            version = dep['version']
            if version != '*' and not SpecItem.re_spec.match(version):
                # Make a spec out of this version
                version = '==' + version

            version = util.Spec(version)
            mod = self._mod._repo.query(dep['id'], version)
            pkgs = dep.get('packages', [])
            found_pkgs = []

            for pkg in mod.packages:
                if pkg.status == 'required' or pkg.name in pkgs:
                    result.append((pkg, version))
                    found_pkgs.append(pkg.name)

            missing_pkgs = set(pkgs) - set(found_pkgs)
            if len(missing_pkgs) > 0:
                raise PackageNotFound('Package %s of mod %s (%s) couldn\'t be found!' % (next(iter(missing_pkgs)), mod.mid, version), mod.mid, missing_pkgs)

        return result

    def check_env(self):
        bvars = None

        for check in self.environment:
            value = check['value'].lower()
            c_type = check['type'].lower()

            if c_type == 'os':
                if value == 'windows':
                    if sys.platform not in ('win32', 'cygwin'):
                        return False
                elif value == 'linux':
                    if not sys.platform.startswith('linux'):
                        return False
                elif value == 'macos':
                    if sys.platform != 'darwin':
                        return False
                else:
                    return False

            elif c_type == 'cpu_feature':
                if CPU_INFO is None:
                    # We don't have any information on the current CPU so we just ignore this check.
                    return True

                if value in CPU_INFO['flags']:
                    return True

                if value.upper() == CPU_INFO['arch']:
                    return True

                return False
            elif c_type == 'bool':
                if bvars is None:
                    bvars = {}
                    bvars[CPU_INFO['arch']] = True  # this is either X86_32 or X86_64

                    if sys.platform in ('win32', 'cygwin'):
                        bvars['windows'] = True
                    elif sys.platform.startswith('linux'):
                        bvars['linux'] = True
                    elif sys.platform == 'darwin':
                        bvars['macosx'] = True
                    else:
                        logging.error('You are using an unrecognized OS! (%s)' % sys.platform)

                    for flag in CPU_INFO['flags']:
                        bvars[flag] = True

                return self._solve_bool(value, bvars)

        return True

    @classmethod
    def _solve_bool(cls, expr, vars):
        if expr[0] == 'var':
            return vars.get(expr[1])
        elif expr[0] == 'not':
            return not cls._solve_bool(expr[1], vars)
        elif expr[0] == 'and':
            return cls._solve_bool(expr[1], vars) and cls._solve_bool(expr[2], vars)
        elif expr[0] == 'or':
            return cls._solve_bool(expr[1], vars) or cls._solve_bool(expr[2], vars)
        else:
            raise Exception('Unknown operation %s! (%s)' % (expr[0], expr))


# Keeps track of installed mods
class InstalledRepo(Repo):
    base = '[INSTALLED]'

    def clear(self):
        self.mods = {}

    def save_pins(self, path):
        with open(path, 'w') as stream:
            json.dump(self.pins, stream)

    def load_pins(self, path):
        with open(path, 'r') as stream:
            self.pins = json.load(stream)

    def set(self, mods):
        for m, v in mods['pins'].items():
            self.pins[m] = semantic_version.Version(v)

        for mod in mods['mods']:
            self.add_mod(InstalledMod(mod))

    def add_pkg(self, pkg):
        mod = pkg.get_mod()
        try:
            my_mod = self.query(mod)
        except ModNotFound:
            my_mod = InstalledMod.convert(mod)
            my_pkg = my_mod.add_pkg(pkg)
            self.add_mod(my_mod)
            return my_pkg
        else:
            return my_mod.add_pkg(pkg)

    def del_pkg(self, pkg):
        mod = pkg.get_mod()

        try:
            my_mod = self.query(mod)
        except ModNotFound:
            logging.error('Tried to delete non-existing package!')
            return

        my_mod.del_pkg(pkg)

    def del_mod(self, mod):
        if mod.mid in self.mods:
            vs = self.mods[mod.mid]
            rem = None
            for m in vs:
                if m.version == mod.version:
                    rem = m
                    break

            if rem is None:
                logging.error('Tried to delete missing mod version!')
            else:
                vs.remove(rem)
                if len(vs) == 0:
                    del self.mods[mod.mid]

    def is_installed(self, mid, spec=None, pname=None):
        try:
            self.query(mid, spec, pname)
            return True
        except ModNotFound:
            return False

    def get_updates(self):
        remote_mods = center.mods
        updates = {}

        for mid, mods in self.mods.items():
            try:
                rem_mod = remote_mods.query(mid)
            except ModNotFound:
                continue

            if rem_mod.version > mods[0].version:
                # Let's see if the files changed.
                my_files = {}
                rem_files = {}
                my_pkgs = [pkg.name for pkg in mods[0].packages]

                for item in mods[0].get_files():
                    my_files[item['filename']] = item['md5sum']

                for item in rem_mod.get_files():
                    if item['package'] in my_pkgs:
                        rem_files[item['filename']] = item['md5sum']

                if rem_files == my_files:
                    logging.warning('Detected an empty update for mod "%s"! (%s -> %s)', mods[0].title, str(mods[0].version), str(rem_mod.version))
                    # TODO: Resolve this situation! (Update the local metadata?)
                else:
                    if mid not in updates:
                        updates[mid] = {}

                    updates[mid][mods[0].version] = rem_mod.version

        return updates


class InstalledMod(Mod):
    check_notes = ''
    folder = None
    _path = None

    @staticmethod
    def load(path):
        if path.endswith('.json'):
            with open(path, 'r') as stream:
                data = json.load(stream)

            mod = InstalledMod(data)
            mod._path = path
        elif path.lower().endswith('.ini'):
            mod = IniMod()
            mod.load(path)
        else:
            return None

        mod.folder = os.path.dirname(path)
        if mod.logo is not None and '://' not in mod.logo:
            mod.logo_path = os.path.join(os.path.dirname(path), mod.logo)

        if mod.tile is not None and '://' not in mod.tile:
            mod.tile_path = os.path.join(os.path.dirname(path), mod.tile)

        return mod

    @staticmethod
    def convert(mod):
        data = mod.get()
        data['packages'] = []

        # IMPORTANT: This code decides where newly installed mods are stored.
        base = center.settings['base_path']
        if data['type'] == 'engine':
            data['folder'] = os.path.join(base, 'bin', data['id']) + '-' + data['version']
        elif data['type'] == 'tc':
            data['folder'] = os.path.join(base, data['id'])
        else:
            data['folder'] = os.path.join(base, data['parent'], data['id'])

        nmod = InstalledMod(data)
        nmod.logo_path = mod.logo_path
        return nmod

    def __init__(self, values=None):
        super(InstalledMod, self).__init__(values)

    def set(self, values):
        pkgs = values.get('packages', [])
        values = values.copy()
        values['packages'] = []

        super(InstalledMod, self).set(values)
        
        if 'folder' in values:
            self.folder = values['folder']

        self.check_notes = values.get('check_notes', '')
        for pkg in pkgs:
            self.packages.append(InstalledPackage(pkg, self))

    def get(self):
        return {
            'installed': True,
            'id': self.mid,
            'title': self.title,
            'type': self.mtype,
            'parent': self.parent,
            'version': str(self.version),
            'description': self.description,
            'logo': self.logo,
            'logo_path': self.logo_path,
            'tile': self.tile,
            'tile_path': self.tile_path,
            'release_thread': self.release_thread,
            'videos': self.videos,
            'first_release': self.first_release.strftime('%Y-%m-%d') if self.first_release else None,
            'last_update': self.last_update.strftime('%Y-%m-%d') if self.last_update else None,
            'cmdline': self.cmdline,
            'packages': [pkg.get() for pkg in self.packages]
        }

    def set_base(self, base):
        pass

    def add_pkg(self, pkg):
        pkg = InstalledPackage.convert(pkg, self)
        found = False

        for i, p in enumerate(self.packages):
            if p.name == pkg.name:
                self.packages[i] = pkg
                found = True
                break

        if not found:
            self.packages.append(pkg)

        return pkg

    def del_pkg(self, pkg):
        for i, p in enumerate(self.packages):
            if p.name == pkg.name:
                del self.packages[i]
                break

    def save(self):
        modpath = self.folder
        im_path = util.ipath(modpath)

        # Correct the casing of our folder if neccessary.
        if im_path != modpath:
            modpath = im_path
            self.folder = modpath

        path = os.path.join(modpath, 'mod.json')
        info = self.get()

        if self.logo is not None and not self.logo.startswith('knossos.'):
            logo = os.path.join(modpath, 'knossos.' + self.logo.split('.')[-1])

            if os.path.abspath(logo) != os.path.abspath(self.logo):
                # Copy the logo right next to the json file.
                shutil.copy(self.logo, logo)

            info['logo'] = os.path.basename(logo)

        with open(path, 'w') as stream:
            json.dump(info, stream)

    def get_mod_flag(self):
        return []

    def get_executables(self):
        deps = self.resolve_deps(True)
        skipped = set()
        exes = []

        for pkg in deps:
            mod = pkg.get_mod()
            if mod.mid in skipped:
                continue

            if mod.mtype != 'engine':
                skipped.add(mod.mid)
                continue

            for exe in pkg.executables:
                exe = exe.copy()
                exe['file'] = os.path.join(mod.folder, exe['file'])
                exes.append(exe)

        if not exes:
            # I'll enable this part once all mods are migrated (i.e. have FSO or another engine added to their dependencies).
            # raise Exception('No engine found for "%s"!' % self.title)
            
            # For now we just use FSO.
            mod = center.installed.query('FSO')
            if not mod:
                raise Exception('No engine found for "%s"!' % self.title)

            for pkg in mod.packages:
                for exe in pkg.executables:
                    exe = exe.copy()
                    exe['file'] = os.path.join(mod.folder, exe['file'])
                    exes.append(exe)

        return exes


class IniMod(InstalledMod):
    _pr_list = None
    _sc_list = None

    def __init__(self, values=None):
        super(IniMod, self).__init__(values)

        self._pr_list = []
        self._sc_list = []

        self.version = semantic_version.Version('1.0.0+ini')

    def load(self, path):
        with open(path, 'r') as stream:
            for line in stream:
                if '=' not in line:
                    continue

                line = line.split('=')
                name = line[0].strip()
                value = line[1].strip(' \r\n\t;')

                # Skip empty values
                if value == '':
                    continue

                if name == 'modname':
                    self.title = value + ' (ini)'
                elif name == 'infotext':
                    self.description = value
                elif name.startswith('image'):
                    self.logo = value
                elif name == 'primarylist':
                    self._pr_list = value.split(',')
                elif name in ('secondarylist', 'secondrylist'):
                    self._sc_list = value.split(',')

        self.folder = os.path.basename(os.path.dirname(path))
        if self.title == '':
            self.title = self.folder + ' (ini)'

        self.mid = '##INI_COMPAT#' + self.folder
        if self.logo:
            self.logo_path = os.path.join(path, self.logo)

        pkg = InstalledPackage({
            'name': 'Content',
            'status': 'required'
        }, self)
        self.add_pkg(pkg)

    def get_mod_flag(self):
        mods = self._pr_list[:]
        mods.append(self.folder)
        mods.extend(self._sc_list)

        return mods


class InstalledPackage(Package):
    check_notes = ''
    files_ok = -1
    files_checked = -1

    @staticmethod
    def convert(pkg, mod):
        return InstalledPackage(pkg.get(), mod)

    def set(self, values):
        super(InstalledPackage, self).set(values.copy())

        self.check_notes = values.get('check_notes', '')

    def get(self):
        data = super(InstalledPackage, self).get()
        data['check_notes'] = self.check_notes
        return data
