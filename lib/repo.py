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
from lib import util

# You have to fill this list using https://github.com/workhorsy/py-cpuinfo .
CPU_FLAGS = []


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
        self.parse(open(path, 'r'))

    def parse(self, obj):
        if isinstance(obj, str):
            data = json.loads(obj)
        else:
            with obj:
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

    def query(self, mid, spec):
        if mid not in self.mods:
            raise ModNotFound('Mod "%s" wasn\'t found!' % (mid), mid)

        candidates = self.mods[mid]
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
        for pkg in pkgs:
            for dep, version in pkg.resolve_deps():
                mid = dep.get_mod().mid

                if mid not in dep_dict:
                    dep_dict[mid] = {}

                if dep.name not in dep_dict[mid]:
                    dep_dict[mid][dep.name] = []

                dep_dict[mid][dep.name].append((dep, version))

        dep_list = []
        for mid, deps in dep_dict.items():
            for name, variants in deps.items():
                if len(variants) == 1:
                    dep_list.append(variants[0])
                else:
                    specs = [item[1] for item in variants]
                    remains = []

                    for v in variants:
                        ok = True
                        for spec in specs:
                            if not spec.match(v.get_mod().version):
                                ok = False
                                break

                        if ok:
                            remains.append(v)

                    if len(remains) == 0:
                        raise PackageNotFound('No version of package "%s" found for these constraints: %s' % (variants[0].name, ','.join(specs)), mid, variants[0].name)
                    else:
                        # Pick the latest
                        remains.sort(key=lambda v: v.version)
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

        pkgs = [Package(pkg, self) for pkg in values.get('packages', [])]
        self.packages = [pkg for pkg in pkgs if pkg.check_env()]

    def get_submods(self):
        return [self._repo.query(mid, semantic_version.Spec('=*')) for mid in self.submods]

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
    status = 'required'
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
        self.status = values.get('status', '')
        self.dependencies = values.get('dependencies', [])
        self.environment = values.get('environment', [])
        self.files = values.get('files', {})

    def get_mod(self):
        return self._mod

    def get_files(self):
        files = {}
        for name, item in self.files.items():
            if item['is_archive']:
                for path, csum in item['contents'].items():
                    files[os.path.join(item['dest'], path)] = (csum, name)
            else:
                files[os.path.join(item['dest'], name)] = item['md5sum']

        return files

    def resolve_deps(self):
        result = []
        for dep in self.dependencies:
            version = dep['version']
            if re.match('\d.*', version):
                # Make spec out of this version
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
                if check['os'] == 'windows':
                    if sys.platform not in ('win32', 'cygwin'):
                        return False
                elif check['os'] == 'linux':
                    if not sys.platform.startswith('linux'):
                        return False
                elif check['os'] == 'macos':
                    if sys.platform != 'darwin':
                        return False
                else:
                    return False

            elif check['type'] == 'cpu_feature':
                return check['feature'] in CPU_FLAGS

        return True
