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

from . import center, util, bool_parser

# You have to fill this using https://github.com/workhorsy/py-cpuinfo .
CPU_INFO = None
STABILITES = ('nightly', 'rc', 'stable')


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


class NoExecutablesFound(Exception):
    pass


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

        if len(mod.packages) == 0 and not isinstance(mod, InstalledMod):
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
            raise ModNotFound('Mod "%s" (%s) could not be removed from %s!' % (mid, mod.version, self.base), mid=mid)

        idx = None
        for i, item in enumerate(self.mods[mid]):
            if item.version == mod.version:
                idx = i
                break

        if not idx:
            raise ModNotFound('Mod "%s" (%s) could not be removed from %s because the exact version was missing!' % (mid, mod.version, self.base), mid=mid)

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

            if candidates[0].mtype == 'engine':
                # Multiple versions qualify and this is an engine so we have to check the stability next
                stab = center.settings['engine_stability']
                if stab not in STABILITES:
                    stab = STABILITES[-1]

                stab_idx = STABILITES.index(stab)
                version = None
                while stab_idx > -1:
                    version = spec.select([mod.version for mod in candidates if mod.stability == stab])
                    if not version:
                        # Nothing found, try the next lower stability
                        stab_idx -= 1
                        stab = STABILITES[stab_idx]
                    else:
                        # Found at least one result
                        break

                if not version:
                    version = spec.select([mod.version for mod in candidates])
            else:
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
    def process_pkg_selection(self, pkgs, recursive=True):
        dep_dict = {}
        ndeps = pkgs

        for pkg in pkgs:
            mod = pkg.get_mod()
            dd = dep_dict.setdefault(mod.mid, {})

            version = str(mod.version)
            if version != '*' and not SpecItem.re_spec.match(version):
                # Make a spec out of this version
                version = '==' + version

            dd = dd.setdefault(util.Spec(version), {})
            dd['#mod'] = pkg.get_mod()
            dd[pkg.name] = pkg

        # Resolve the pkgs' dependencies
        while len(ndeps) > 0:
            _nd = ndeps
            ndeps = []

            for pkg in _nd:
                for dep, version in pkg.resolve_deps():
                    dd = dep_dict.setdefault(dep.get_mod().mid, {})
                    dd = dd.setdefault(version, {})
                    dd['#mod'] = dep.get_mod()

                    if dep.name not in dd:
                        dd[dep.name] = dep
                        if recursive:
                            ndeps.append(dep)

        # Check for conflicts (and try to resolve them if possible).
        dep_list = set()
        pref_stable = center.settings['engine_stability']
        for mid, variants in dep_dict.items():
            if len(variants) == 1:
                # This loop only iterates once but it's the easiest solution to get the actual value
                for pkgs in variants.values():
                    del pkgs['#mod']
                    dep_list |= set(pkgs.values())
            else:
                specs = variants.keys()
                remains = []

                for v in variants.values():
                    ok = True
                    for spec in specs:
                        if not spec.match(v['#mod'].version):
                            ok = False
                            break

                    if ok:
                        remains.append(v)

                if len(remains) == 0:
                    v = (list(variants.values())[0]['#mod'].title, ','.join([str(s) for s in specs]))
                    raise PackageNotFound('No version of mod "%s" found for these constraints: %s' % v, mid, v[0])
                else:
                    if remains[0]['#mod'].mtype == 'engine':
                        # Multiple versions qualify and this is an engine so we have to check the stability next
                        stab = pref_stable
                        if stab not in STABILITES:
                            stab = STABILITES[-1]

                        stab_idx = STABILITES.index(stab)
                        candidates = []
                        while stab_idx > -1:
                            candidates = [m for m in remains if m['#mod'].stability == stab]
                            if len(candidates) == 0:
                                # Nothing found, try the next lower stability
                                stab_idx -= 1
                                stab = STABILITES[stab_idx]
                            else:
                                # Found at least one result
                                break

                        # An empty remains list would trigger an index out of bounds error; avoid that
                        if len(candidates) > 0:
                            remains = candidates

                    # Pick the latest
                    remains.sort(key=lambda v: v['#mod'].version)
                    del remains[-1]['#mod']
                    dep_list |= set(remains[-1].values())

        return dep_list

    def get_dependents(self, pkgs):
        deps = set()
        mids = set([p.get_mod().mid for p in pkgs])

        for mid, mvs in self.mods.items():
            # Ignore self-references
            if mid not in mids:
                for mod in mvs:
                    try:
                        for dp in self.process_pkg_selection(mod.packages, False):
                            if dp in pkgs:
                                deps.add(mod)
                    except ModNotFound:
                        pass

        return deps


class Mod(object):
    _repo = None
    mid = ''
    title = ''
    mtype = 'mod'
    version = None
    stability = None
    parent = None
    cmdline = ''
    mod_flag = None
    logo = None
    tile = None
    banner = None
    description = ''
    notes = ''
    release_thread = None
    videos = None
    screenshots = None
    attachments = None
    first_release = None
    last_update = None
    actions = None
    packages = None

    __fields__ = ('mid', 'title', 'type', 'version', 'parent', 'cmdline', 'logo', 'tile', 'banner',
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
        self.stability = values.get('stability', 'stable')
        self.parent = values.get('parent', 'FS2')
        self.cmdline = values.get('cmdline', '')
        self.mod_flag = values.get('mod_flag', None)
        self.description = values.get('description', '')
        self.notes = values.get('notes', '')
        self.release_thread = values.get('release_thread', None)
        self.videos = values.get('videos', [])
        self.screenshots = values.get('screenshots', [])
        self.attachments = values.get('attachments', [])
        self.first_release = values.get('first_release', None)
        self.last_update = values.get('last_update', None)
        self.actions = values.get('actions', [])

        self.packages = []

        installed = isinstance(self, InstalledMod)
        for pkg in values.get('packages', []):
            p = Package(pkg, self)
            if installed or p.check_env():
                self.packages.append(p)

        base = None
        if hasattr(self, 'folder'):
            base = self.folder
        elif self._repo is not None:
            base = self._repo.base

        if base:
            for prop in ('logo', 'tile', 'banner'):
                if values.get(prop) is not None:
                    if '://' in base:
                        setattr(self, prop, util.url_join(base, values[prop]))
                    elif '://' not in values[prop]:
                        setattr(self, prop, os.path.abspath(os.path.join(base, values[prop])))
                    else:
                        setattr(self, prop, values[prop])

            for prop in ('screenshots', 'attachments'):
                ims = getattr(self, prop)
                for i, path in enumerate(ims):
                    if '://' in base:
                        ims[i] = util.url_join(base, path)
                    elif '://' not in path:
                        ims[i] = os.path.abspath(os.path.join(base, path))

        else:
            for prop in ('logo', 'tile', 'banner'):
                setattr(self, prop, values.get(prop))

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
            'stability': self.stability,
            'parent': self.parent,
            'cmdline': self.cmdline,
            'mod_flag': self.mod_flag,
            'logo': self.logo,
            'tile': self.tile,
            'banner': self.banner,
            'description': self.description,
            'notes': self.notes,
            'release_thread': self.release_thread,
            'videos': self.videos,
            'screenshots': self.screenshots,
            'attachments': self.attachments,
            'first_release': self.first_release.strftime('%Y-%m-%d') if self.first_release else None,
            'last_update': self.last_update.strftime('%Y-%m-%d') if self.last_update else None,
            'actions': self.actions,
            'packages': [pkg.get() for pkg in self.packages]
        }

    def copy(self):
        return self.__class__(self.get(), self._repo)

    def get_files(self):
        files = []
        for pkg in self.packages:
            for item in pkg.filelist:
                item = item.copy()
                item['package'] = pkg.name
                files.append(item)

        return files

    def resolve_deps(self, only_required=True, recursive=True):
        if only_required:
            pkgs = [pkg for pkg in self.packages if pkg.status == 'required']
        else:
            pkgs = [pkg for pkg in self.packages if pkg.status in ('required', 'recommended')]

        return self._repo.process_pkg_selection(pkgs, recursive=recursive)

    def get_parent(self):
        if self.parent:
            return self._repo.query(self.parent)
        else:
            return None

    def get_dependents(self):
        return self._repo.get_dependents(self.packages)


class Package(object):
    _mod = None
    name = ''
    notes = ''
    status = 'recommended'
    dependencies = None
    environment = None
    folder = None
    is_vp = False
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
        self.environment = values.get('environment', '')
        self.folder = values.get('folder', self.name)
        self.is_vp = values.get('is_vp', False)
        self.files = {}
        self.filelist = values.get('filelist', [])
        self.executables = []

        if self.folder is None:
            self.folder = self.name

        for exe in values.get('executables', []):
            self.executables.append({
                'file': exe['file'],
                'label': exe.get('label', None)
            })

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

        if self._mod:
            mid = self._mod.mid
            if mid == '':
                raise Exception('Package "%s" initialized with Mod %s which has no ID!' % (self.name, self._mod.title))

    def get(self):
        return {
            'name': self.name,
            'notes': self.notes,
            'status': self.status,
            'dependencies': self.dependencies,
            'environment': self.environment,
            'folder': self.folder,
            'is_vp': self.is_vp,
            'files': list(self.files.values()),
            'filelist': self.filelist,
            'executables': self.executables
        }

    def get_mod(self):
        return self._mod

    def get_files(self):
        files = {}
        for name, item in self.files.items():
            for path, csum in item['contents'].items():
                files[os.path.join(item['dest'], path)] = (csum, name)

        return files

    def resolve_deps(self):
        result = []
        for dep in self.dependencies:
            version = dep.get('version', '*') or '*'
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
        if self.environment in ('', None):
            return True

        if not isinstance(self.environment, str):
            logging.warning('Invalid value for environment check in mod %s (%s)!' % (self._mod.mid, self._mod.version))
            return True

        bvars = {}
        bvars[CPU_INFO['arch'].lower()] = True  # this is either X86_32 or X86_64

        if sys.platform in ('win32', 'cygwin'):
            bvars['windows'] = True
        elif sys.platform.startswith('linux'):
            bvars['linux'] = True
        elif sys.platform == 'darwin':
            bvars['macosx'] = True
        else:
            logging.error('You are using an unrecognized OS! (%s)' % sys.platform)

        for flag in CPU_INFO['flags']:
            bvars[flag.lower()] = True

        try:
            return bool_parser.eval_string(self.environment, bvars)
        except Exception:
            logging.exception('Failed to evaluate expression "%s"!' % self.environment)

            # Since we can't perform this check, just assume that it returns True as otherwise this mod would be
            # inaccessible.
            return True


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
                    my_files[item['filename']] = item['checksum']

                for item in rem_mod.get_files():
                    if item['package'] in my_pkgs:
                        rem_files[item['filename']] = item['checksum']

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
    dev_mode = False
    custom_build = None
    user_exe = None
    user_cmdline = None
    user_custom_build = None
    _path = None

    @staticmethod
    def load(path):
        if path.endswith('.json'):
            with open(path, 'r') as stream:
                data = json.load(stream)

            mod = InstalledMod(None)
            mod.folder = os.path.normpath(os.path.dirname(path))
            mod.set(data)

            user_path = os.path.join(os.path.dirname(path), 'user.json')
            if os.path.isfile(user_path):
                try:
                    with open(user_path, 'r') as stream:
                        mod.set_user(json.load(stream))
                except Exception:
                    logging.exception('Failed to load user data for %s!' % mod)

            return mod
        else:
            return None

    @staticmethod
    def convert(mod):
        data = mod.get()
        data['packages'] = []

        nmod = InstalledMod(data)
        nmod.generate_folder()
        return nmod

    def set(self, values):
        pkgs = values.get('packages', [])
        values = values.copy()
        values['packages'] = []

        super(InstalledMod, self).set(values)

        if 'folder' in values:
            self.folder = values['folder']

        self.dev_mode = values.get('dev_mode', False)
        self.custom_build = values.get('custom_build', None)
        self.check_notes = values.get('check_notes', '')

        if not self.mod_flag:
            # Fix broken metadata
            self.update_mod_flag()

        for pkg in pkgs:
            installed_pkg = InstalledPackage(pkg, self)
            # If the user installed packages on multiple platforms into the same directory then an installed package
            # may be present that is not valid for the current environment so we need to check that here
            if installed_pkg.check_env():
                self.packages.append(installed_pkg)

    def set_user(self, values):
        self.user_exe = values.get('exe')
        self.user_cmdline = values.get('cmdline')
        self.user_custom_build = values.get('custom_build')

    def get(self):
        return {
            'installed': True,
            'id': self.mid,
            'title': self.title,
            'type': self.mtype,
            'parent': self.parent,
            'version': str(self.version),
            'stability': self.stability,
            'description': self.description,
            'notes': self.notes,
            'folder': self.folder,
            'logo': self.logo,
            'tile': self.tile,
            'banner': self.banner,
            'release_thread': self.release_thread,
            'videos': self.videos,
            'screenshots': self.screenshots[:],
            'attachments': self.attachments[:],
            'first_release': self.first_release.strftime('%Y-%m-%d') if self.first_release else None,
            'last_update': self.last_update.strftime('%Y-%m-%d') if self.last_update else None,
            'cmdline': self.cmdline,
            'mod_flag': self.mod_flag,
            'dev_mode': self.dev_mode,
            'custom_build': self.custom_build,
            'packages': [pkg.get() for pkg in self.packages],

            'user_exe': self.user_exe,
            'user_cmdline': self.user_cmdline,
            'user_custom_build': self.user_custom_build
        }

    def get_user(self):
        return {
            'exe': self.user_exe,
            'cmdline': self.user_cmdline,
            'custom_build': self.user_custom_build
        }

    def get_relative(self):
        info = self.get()

        # Storing the folder of the JSON file inside the file would be silly.
        del info['folder']
        del info['user_exe']
        del info['user_cmdline']
        del info['user_custom_build']

        # Make sure we only store relative paths.
        for prop in ('logo', 'tile', 'banner'):
            if info[prop] and '://' not in info[prop]:
                info[prop] = os.path.relpath(info[prop], self.folder)

        for prop in ('screenshots', 'attachments'):
            paths = info[prop]
            for i, p in enumerate(paths):
                paths[i] = os.path.relpath(p, self.folder)

        return info

    def copy(self):
        return InstalledMod(self.get(), self._repo)

    def generate_folder(self):
        # IMPORTANT: This code decides where newly installed mods are stored.
        base = os.path.normpath(center.settings['base_path'])
        meta = self.get_relative()

        if self.mtype in ('engine', 'tool'):
            self.folder = os.path.join(base, 'bin', self.mid)
        elif self.mtype == 'tc':
            self.folder = os.path.join(base, self.mid, self.mid)
        else:
            self.folder = os.path.join(base, self.parent, self.mid)

        self.folder += '-' + str(self.version)

        # This should update the paths to images, etc. since get_relative() only returns relative paths
        self.set(meta)

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
        im_path = util.ipath(self.folder)

        # Correct the casing of our folder if neccessary.
        if im_path != self.folder:
            self.folder = im_path

        with open(os.path.join(self.folder, 'mod.json'), 'w') as stream:
            json.dump(self.get_relative(), stream, indent=4)

    def save_user(self):
        modpath = self.folder
        im_path = util.ipath(modpath)

        # Correct the casing of our folder if neccessary.
        if im_path != modpath:
            modpath = im_path
            self.folder = modpath

        path = os.path.join(modpath, 'user.json')

        with open(path, 'w') as stream:
            json.dump(self.get_user(), stream)

    def update_mod_flag(self):
        old_list = self.mod_flag
        new_list = set([self.mid])

        if old_list is None:
            old_list = []

        # Collect all dependency IDs
        for pkg in self.packages:
            for dep in pkg.dependencies:
                mod = self._repo.query(dep['id'])
                if mod and mod.mtype not in ('tool', 'engine'):
                    new_list.add(dep['id'])

        # Remove old IDs which have been removed from our dependencies
        for i, mid in reversed(list(enumerate(old_list))):
            if mid not in new_list:
                del old_list[i]

        # Add new IDs which have been added to our dependencies
        for mid in new_list:
            if mid not in old_list:
                old_list.append(mid)

        self.mod_flag = old_list

    def get_mod_flag(self):
        # Since mod_flag is just a list of IDs, we have to look up their paths here.
        paths = []
        dev_involved = False
        mods = {}

        # We have to retrieve the mods this way to honor the version constraints
        for pkg in self._repo.process_pkg_selection(self.packages):
            mod = pkg.get_mod()

            if mod.mid not in mods:
                mods[mod.mid] = mod

        for mid in self.mod_flag:
            if mid not in mods:
                # We don't know if this is an optional dependency; ignore it for now.
                logging.debug('Skipping mod "%s" during -mod generation because it\'s missing.' % mid)
                continue

            mod = mods[mid]
            if mod.dev_mode:
                for pkg in mod.packages:
                    if pkg.check_env():
                        paths.append((os.path.join(mod.folder, pkg.folder), '%s - %s' % (mod.title, pkg.name)))
                        dev_involved = True

            else:
                paths.append((mod.folder, mod.title))

        return paths, dev_involved

    def get_executables(self, user=False):
        exes = []
        if user and self.user_custom_build:
                exes.append({
                    'file': self.user_custom_build,
                    'mod': self,
                    'label': None
                })

        if self.custom_build:
            exes.append({
                'file': self.custom_build,
                'mod': self,
                'label': None
            })

        if self.mtype in ('engine', 'tool'):
            deps = self.packages
        else:
            try:
                deps = self.resolve_deps(True, False)
            except ModNotFound:
                logging.exception('Error during dep resolve for executables!')
                deps = []

        if user and self.user_exe:
            try:
                exe_mod = self._repo.query(self.user_exe[0], util.Spec('==' + self.user_exe[1]))
                deps = exe_mod.packages + list(deps)
            except ModNotFound:
                pass

        for pkg in deps:
            mod = pkg.get_mod()
            if mod.mtype != 'engine' or (mod.dev_mode and not pkg.check_env()):
                continue

            for exe in pkg.executables:
                exe = exe.copy()
                pkgpath = mod.folder
                if mod.dev_mode:
                    pkgpath = os.path.join(pkgpath, pkg.folder)

                exe['file'] = os.path.join(pkgpath, exe['file'])
                exe['mod'] = mod
                exes.append(exe)

        if not exes:
            raise NoExecutablesFound('No engine found for "%s"!' % self.title)

        return exes


class IniMod(InstalledMod):
    _pr_list = None
    _sc_list = None

    def __init__(self, values=None):
        super(IniMod, self).__init__(values)

        self._pr_list = []
        self._sc_list = []

        self.version = semantic_version.Version('1.0.0')

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
                    self.title = value
                elif name == 'infotext':
                    self.description = value
                elif name.startswith('image'):
                    self.logo = value
                elif name == 'primarylist':
                    self._pr_list = value.split(',')
                elif name in ('secondarylist', 'secondrylist'):
                    self._sc_list = value.split(',')

        self.folder = os.path.dirname(path)
        if self.title == '':
            self.title = os.path.basename(self.folder)

        self.mid = os.path.basename(self.folder)
        if self.logo:
            self.logo_path = os.path.join(path, self.logo)

        pkg = InstalledPackage({
            'name': 'Content',
            'status': 'required'
        }, self)

        # Set some default values
        self.screenshots = []
        self.attachments = []

        self.add_pkg(pkg)

    def get_mod_flag(self):
        mods = self._pr_list[:]
        mods.append(self.folder)
        mods.extend(self._sc_list)

        return mods

    def get_primary_list(self):
        return self._pr_list

    def get_secondary_list(self):
        return self._sc_list


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
