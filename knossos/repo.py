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

import sys
import os
import logging
import json
import re
import tempfile
import shutil
import semantic_version
import six
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

    def __init__(self, data=None):
        self.mods = {}

        if data is not None:
            self.set(data)

    def set(self, mods):
        for mod in mods:
            self.add_mod(Mod(mod, self))

    def get(self):
        mods = []
        for v in self.mods.values():
            for mod in v:
                mods.append(mod.get())

        return mods

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
            if mod.get('logo', None) is not None and self.base is not None and '://' not in mod['logo']:
                if self.is_link:
                    mod['logo'] = util.url_join(self.base, mod['logo'])
                else:
                    mod['logo'] = os.path.join(self.base, mod['logo'])

            self.add_mod(Mod(mod, self))

    def add_mod(self, mod):
        mid = mod.mid
        if mid in self.mods:
            inserted = False

            for i, item in enumerate(self.mods[mid]):
                if item.version == mod.version:
                    logging.info('Mod "%s" (%s) from "%s" overwrites an existing mod version!', mid, mod.version, self.base)

                    self.mods[mid][i] = mod
                    inserted = True
                    break

            if not inserted:
                self.mods[mid].append(mod)
                self.mods[mid].sort(key=lambda m: m.version, reverse=True)
        else:
            self.mods[mid] = [mod]

        mod._repo = self

    def merge(self, repo):
        for mod in repo.get_list():
            self.add_mod(mod)

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

        candidates = self.mods[mid]
        if spec is None:
            mod = candidates[0]
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
            if spec.match(mod.version):
                yield mod

    def get_tree(self):
        submod_ids = []
        for mid, mod in self.mods.items():
            submod_ids.extend(mod[0].submods)

        roots = set(self.mods.keys()) - set(submod_ids)
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
    version = None
    folder = None
    cmdline = ''
    logo = None
    logo_path = None
    description = ''
    notes = ''
    submods = None
    actions = None
    packages = None

    __fields__ = ('mid', 'title', 'version', 'folder', 'cmdline', 'logo', 'description', 'notes', 'submods', 'actions', 'packages')

    def __init__(self, values=None, repo=None):
        self.actions = []
        self.packages = []

        if repo is not None:
            self._repo = self

        if values is not None:
            self.set(values)

    def set(self, values):
        self.mid = values['id']
        self.title = values['title']
        self.version = semantic_version.Version(values['version'], partial=True)
        self.folder = values.get('folder', self.mid).strip('/')  # make sure we have a relative path
        self.cmdline = values.get('cmdline', '')
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

    def get_submods(self):
        return [self._repo.query(mid) for mid in self.submods]

    def get_files(self):
        files = []
        for pkg in self.packages:
            for item in pkg.filelist:
                item = item.copy()
                item['package'] = pkg.name
                files.append(item)

        return files

    def resolve_deps(self):
        return self._repo.process_pkg_selection([pkg for pkg in self.packages if pkg.status == 'required'])

    def save_logo(self, dest):
        if self.logo is None:
            return

        suffix = '.' + self.logo.split('.')[-1]
        fd, path = tempfile.mkstemp(dir=dest, prefix='logo', suffix=suffix)
        os.close(fd)

        if '://' in self.logo:
            # That's a URL
            with open(path, 'wb') as fobj:
                util.download(self.logo, fobj)
        else:
            shutil.copyfile(self.logo, path)

        self.logo = os.path.relpath(path, dest)
        self.logo_path = os.path.abspath(path)


class Package(object):
    _mod = None
    name = ''
    notes = ''
    status = 'recommended'
    dependencies = None
    environment = None
    files = None
    filelist = None

    def __init__(self, values=None, mod=None):
        self._mod = mod
        self.dependencies = []
        self.environment = []
        self.files = []

        if values is not None:
            self.set(values)

    def set(self, values):
        self.name = values['name']
        self.notes = values.get('notes', '')
        self.status = values.get('status', 'recommended').lower()
        self.dependencies = values.get('dependencies', [])
        self.environment = values.get('environment', [])
        self.files = {}
        self.filelist = values.get('filelist', [])

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
            'filelist': self.filelist
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
            if re.match('\d.*', version):
                # Make a spec out of this version
                version = '==' + version

            version = semantic_version.Spec(version)
            mod = self._mod._repo.query(dep['id'], version)
            pkgs = dep.get('packages', [])
            found_pkgs = []

            for pkg in mod.packages:
                if pkg.status == 'required' or pkg.name in pkgs:
                    result.append((pkg, version))
                    found_pkgs.append(pkg.name)

            missing_pkgs = set(pkgs) - set(found_pkgs)
            if len(missing_pkgs) > 0:
                raise PackageNotFound('Package %s of mod %s (%s) couldn\'t be found!' % (missing_pkgs[0], mod.mid, version))

        return result

    def check_env(self):
        for check in self.environment:
            if check['type'] == 'os':
                if check['value'] == 'windows':
                    if sys.platform not in ('win32', 'cygwin'):
                        return False
                elif check['value'] == 'linux':
                    if not sys.platform.startswith('linux'):
                        return False
                elif check['value'] == 'macos':
                    if sys.platform != 'darwin':
                        return False
                else:
                    return False

            elif check['type'] == 'cpu_feature':
                return CPU_INFO is None or check['value'] in CPU_INFO['flags']

        return True


# Keeps track of installed mods
class InstalledRepo(Repo):

    def clear(self):
        self.mods = {}

    def set(self, mods):
        for mod in mods:
            self.add_mod(InstalledMod(mod))

    def add_pkg(self, pkg):
        mod = pkg.get_mod()
        try:
            my_mod = self.query(mod)
        except ModNotFound:
            my_mod = InstalledMod.convert(mod)
            self.add_mod(my_mod)

        return my_mod.add_pkg(pkg)

    def del_pkg(self, pkg):
        mod = pkg.get_mod()

        try:
            my_mod = self.query(mod)
        except ModNotFound:
            logging.error('Tried to delete non-existing package!')
            return

        my_mod.del_pkg(pkg)

    def is_installed(self, mid, spec=None, pname=None):
        try:
            self.query(mid, spec, pname)
            return True
        except ModNotFound:
            return False

    def get_updates(self):
        remote_mods = center.settings['mods']
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
                else:
                    if mid not in updates:
                        updates[mid] = {}

                    updates[mid][mods[0].version] = rem_mod.version

        return updates


class InstalledMod(Mod):
    check_notes = ''

    @staticmethod
    def convert(mod):
        data = mod.get()
        data['packages'] = []

        return InstalledMod(data)

    def __init__(self, values=None):
        super(InstalledMod, self).__init__(values)

    def set(self, values):
        pkgs = values.get('packages', [])
        values = values.copy()
        values['packages'] = []
        
        super(InstalledMod, self).set(values)

        self.check_notes = values.get('check_notes', '')
        for pkg in pkgs:
            self.packages.append(InstalledPackage(pkg, self))

    def get(self):
        return {
            'id': self.mid,
            'title': self.title,
            'version': str(self.version),
            'description': self.description,
            'logo': self.logo,
            'cmdline': self.cmdline,
            'packages': [pkg.get() for pkg in self.packages]
        }

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
