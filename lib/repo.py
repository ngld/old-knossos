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

import sys
import os
import logging
import json
import re
import tempfile
import shutil
import semantic_version
import six
from lib import util

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

    def __init__(self):
        self.mods = {}

    def get(self, link):
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
                item.get(util.url_join(self.base, inc))
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
                self.mods[mid].sort(key=lambda m: m.version, reversed=True)
        else:
            self.mods[mid] = [mod]

        mod._repo = self

    def merge(self, repo):
        for mod in repo.get_list():
            self.add_mod(mod)

    def query(self, mid, spec=None):
        if mid not in self.mods:
            raise ModNotFound('Mod "%s" wasn\'t found!' % (mid), mid)

        candidates = self.mods[mid]
        if spec is None:
            return candidates[0]

        version = spec.select([mod.version for mod in candidates])
        if not version:
            raise ModNotFound('Mod "%s" %s wasn\'t found!' % (mid, spec), mid, spec)

        for mod in candidates:
            if mod.version == version:
                return mod

        # This should never be reached!
        logging.fatal('Repo.query() unreachable reached!')
        raise ModNotFound('I got confused by the mod versions!', mid, spec)

    def query_all(self, mid, spec):
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

        dep_list = []
        for mid, deps in dep_dict.items():
            for name, variants in deps.items():
                if len(variants) == 1:
                    dep_list.append(next(iter(variants.values())))
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
                        raise PackageNotFound('No version of package "%s" found for these constraints: %s' % (list(variants.values())[0].name, ','.join(specs)), mid, list(variants.values())[0].name)
                    else:
                        # Pick the latest
                        remains.sort(key=lambda v: v.get_mod().version)
                        dep_list.append(remains[-1])

        return pkgs + dep_list

    def save_logos(self, path):
        for mod in self.get_list():
            mod.save_logo(path)


class Mod(object):
    _repo = None
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

    __fields__ = ('mid', 'title', 'version', 'folder', 'logo', 'description', 'notes', 'submods', 'actions', 'packages')

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
        self.folder = values.get('folder', '')
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

    def get_submods(self):
        return [self._repo.query(mid) for mid in self.submods]

    def get_files(self):
        files = {}
        for pkg in self.packages:
            files.update(pkg.get_files())

        return files

    def resolve_deps(self):
        return self._repo.process_pkg_selection(self.packages)

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


class Package(object):
    _mod = None
    name = ''
    notes = ''
    status = 'recommended'
    dependencies = None
    environment = None
    files = None

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
        self.status = values.get('status', 'recommended')
        self.dependencies = values.get('dependencies', [])
        self.environment = values.get('environment', [])
        self.files = {}

        _files = values.get('files', [])

        if isinstance(_files, dict):
            self.files = _files
            for name, item in _files.items():
                item['filename'] = name

        elif isinstance(_files, list):
            for item in _files:
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
            'files': list(self.files.values())
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
class InstalledRepo(object):
    mods = None

    def __init__(self, values=None):
        self.mods = {}

        if values is not None:
            self.set(values)

    def set(self, values):
        self.mods = {}

        for d in values:
            mod = InstalledMod(d)
            self.mods[mod.mid] = mod

    def get(self):
        return [mod.get() for mod in self.mods.values()]

    def add_pkg(self, pkg):
        mod = pkg.get_mod()

        if mod.mid not in self.mods:
            self.mods[mod.mid] = InstalledMod.convert(mod)
        
        return self.mods[mod.mid].add_pkg(pkg)

    def del_pkg(self, pkg):
        mod = pkg.get_mod()

        if mod.mid in self.mods:
            m = self.mods[mod.mid]
            m.del_pkg(pkg)

            # Remove empty mods.
            if len(m.packages) < 1:
                del self.mods[mod.mid]

    def query(self, mid, pname=None):
        if mid not in self.mods:
            #raise ModNotFound('The mod %s could not be found in this InstalledRepo().' % (mid))
            return None

        mod = self.mods[mid]
        if pname is None:
            return mod

        for pkg in mod.packages:
            if pkg.name == pname:
                return pkg

        #raise ModNotFound('The package %s of mod %s (%s) could not be found!' % (pname, mid, mod.name))
        return None

    def is_installed(self, mid, pname=None):
        if pname is None and isinstance(mid, Package):
            pname = mid.name
            mid = mid.get_mod().mid

        pkg = self.query(mid, pname)

        return pkg is not None and pkg.state in ('installed', 'has_update')

    def get_packages(self):
        for mod in self.mods.values():
            for pkg in mod.packages:
                yield pkg


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
        data = super(InstalledMod, self).get()
        data['check_notes'] = self.check_notes
        return data

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
    state = 'unknown'  # installed, not installed, has_update, corrupted
    check_notes = ''
    files_ok = 0
    files_checked = 0
    files_shared = 0

    @staticmethod
    def convert(pkg, mod):
        return InstalledPackage(pkg.get(), mod)

    def set(self, values):
        super(InstalledPackage, self).set(values.copy())

        self.state = values.get('state', 'installed')
        self.check_notes = values.get('check_notes', '')
        self.files_ok = values.get('files_ok', 0)
        self.files_checked = values.get('files_checked', 0)
        self.files_shared = values.get('files_shared', 0)

    def get(self):
        data = super(InstalledPackage, self).get()

        data['state'] = self.state
        data['check_notes'] = self.check_notes
        data['files_ok'] = self.files_ok
        data['files_checked'] = self.files_checked
        data['files_shared'] = self.files_shared

        return data
