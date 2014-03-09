import os
import logging
import shutil
import util
import progress


# Generic classes

class Package(object):
    id = None
    name = None
    version = None
    description = None
    visible = True
    modfolder = None
    dependencies = None
    chksums = None
    hash_algo = 'md5'
    logo = None
    _mod_ini = None
    _repo = None
    _found_path = None
    
    def __init__(self):
        self.subfolders = []
        self.dependencies = []
        self.chksums = []
    
    @staticmethod
    def read(path):
        if path.startswith('http://', 'https://', 'ftp://'):
            return util.get(path)
        else:
            return open(path, 'rb')
    
    def get_full_id(self):
        return (self._repo.id, self.id)
    
    def get_path(self, fs2_path, recheck=False):
        if not recheck and self._found_path is not None and os.path.isdir(self._found_path):
            return self._found_path
        
        paths = [
            [self.modfolder],
            ('fs2mod-py', self.modfolder + '-' + self.version),
            (self.modfolder + '-fs2modpy-' + self.version)
        ]
        
        for path in paths:
            path = util.ipath(os.path.join(fs2_path, *path))
            if os.path.isdir(path) and self.check_installed(path):
                self._found_path = path
                return path
        
        return None
    
    def resolve_deps(self):
        if self._repo is None:
            raise Exception('resolve_deps() called on a lone package!')
        
        return self._repo.resolve_deps(self)
    
    def check_installed(self, modpath):
        info_file = os.path.join(modpath, 'fs2mod-py.info')
        if os.path.isfile(info_file):
            with open(info_file, 'r') as stream:
                if next(stream).strip() == self.id:
                    return True
        
        ini_path = os.path.join(modpath, 'mod.ini')
        if self._mod_ini is not None and os.path.isfile(ini_path):
            with open(ini_path, 'r') as stream:
                for line in stream:
                    if 'modname' in line and self.name in line:
                        return True
                
                return False
        else:
            return self.check_files(modpath)
    
    def setup(self, fs2_path):
        modpath = util.ipath(os.path.join(fs2_path, self.modfolder))
        if os.path.isdir(modpath):
            modpath = util.ipath(os.path.join(fs2_path, 'fs2mod-py', self.modfolder + '-' + self.version))
            if os.path.isdir(modpath):
                raise Exception('This mod is already installed in "%s"!' % (modpath))
        
        os.makedirs(modpath)
        with open(os.path.join(modpath, 'fs2mod-py.info'), 'w') as stream:
            stream.write(self.id + '\n')
            stream.write(self.version + '\n')
            for path, chksum in self.chksums:
                stream.write(path + ' ' + chksum + '\n')
        
        # The actual setup will be handled in subclasses.
        logging.info('Installing %s into %s.', self.name, modpath)
        return modpath
    
    def update(self, modpath):
        info_file = os.path.join(modpath, 'fs2mod-py.info')
        if os.path.isfile(info_file):
            # Remove all old files but ignore those which will be overwritten.
            with open(info_file, 'r') as stream:
                for line in stream[2:]:
                    path, chksum = line.strip().split(' ')
                    full_path = util.ipath(os.path.join(modpath, path))
                    
                    if path not in self.chksums and os.path.isfile(full_path):
                        logging.info('Removing file %s.', path)
                        os.unlink(full_path)
    
    def remove(self, modpath):
        # Is this actually necessary?
        shutil.rmtree(modpath)
    
    def check_files(self, modpath, collect=False):
        corrupt = []
        missing = []
        total = float(len(self.chksums))
        
        for i, (path, chksum) in enumerate(self.chksums):
            progress.update(i / total, path)
            
            full_path = util.ipath(os.path.join(modpath, path))
            if os.path.isfile(full_path):
                real_sum = util.gen_hash(full_path, self.hash_algo)
                if real_sum != chksum:
                    if collect:
                        corrupt.append(path)
                    else:
                        return False
                else:
                    if collect:
                        missing.append(path)
                    else:
                        return False
        
        return corrupt, missing
    
    def get_user_changes(self, modpath, collect=False):
        info_file = os.path.join(modpath, 'fs2mod-py.info')
        if not os.path.isfile(info_file):
            return self.check_files(modpath, collect)
        
        chksums = self.chksums
        self.chksums = dict()
        # Read the installed checksums
        with open(info_file, 'r') as stream:
            for line in stream[2:]:
                path, chksum = line.strip().split(' ')
                self.checksums[path] = chksum
        
        result = self.check_files(modpath, collect)
        self.checksums = chksums
        
        return result


class Repository(object):
    _readers = []
    _packages = None
    _repo_coll = None
    name = None
    id = None
    
    def __init__(self):
        self._packages = dict()
    
    @classmethod
    def add_reader(cls, reader):
        cls._readers.append(reader)
    
    @classmethod
    def read(cls, link):
        for reader in reversed(cls._readers):
            if reader.can_read(link):
                return reader(link)
        
        raise Exception('Unknown repository format for %s.' % (link))
    
    @staticmethod
    def can_read():
        return False
    
    def add_package(self, pkg):
        if not isinstance(pkg, Package):
            raise Exception('Invalid parameter!')
        
        pkg._repo = self
        self._packages[pkg.id] = pkg
    
    def query(self, name):
        for pkg in self._packages.values():
            if pkg.name == name and pkg.visible:
                return pkg
        
        return pkg
    
    def by_id(self, pkg_id):
        return self._packages.get(pkg_id, None)
    
    def get_packages(self):
        return [pkg for pkg in self._packages if pkg.visible]
    
    def resolve_deps(self, pkg):
        if self._repo_coll is not None:
            return self._repo_coll.resolve_deps(pkg)
        else:
            res = []
            
            for id_ in pkg.dependencies:
                if id_[0] != self.id:
                    logging.warning("Can't resolve dependency %s of %s because no RepositoryCollection is known!", id_, pkg)
                else:
                    dep = self.by_id(id_[1])
                    if dep is not None:
                        res.append(dep.get_full_id())
                        res.extend(self.resolve_deps(dep))
                    else:
                        logging.warning("Can't resolve dependency %s of %s.", id_, pkg)
            
            return res


class RepositoryCollection(object):
    _repos = None
    
    def __init__(self):
        self._repos = []
    
    def add_repo(self, repo):
        if not isinstance(repo, Repository):
            repo = Repository.read(repo)
        
        repo._repo_coll = self
        self._repos.append(repo)
    
    def query(self, name):
        for repo in self._repos:
            pkg = repo.query(name)
            if pkg is not None:
                return pkg
        
        return None
    
    def by_id(self, pkg_id):
        repo_id, pkg_id = pkg_id
        for repo in self._repos:
            if repo.id == repo_id:
                return repo.by_id(pkg_id)
        
        return None
    
    def get_repos(self):
        return self._repos[:]
    
    def get_packages(self):
        pkgs = []
        
        for repo in self._repos:
            pkgs.append(repo.get_packages())
        
        return pkgs
    
    def resolve_deps(self, pkg):
        res = []
        
        for id_ in pkg.dependencies:
            dep = self.by_id(id_)
            if dep is not None:
                res.append(dep.get_full_id())
                res.extend(self.resolve_deps(dep))
            else:
                logging.warning('Missing dep %s of %s.', id_, pkg)
        
        return res


# This implements the typical archive download and extraction.
class ArchivePackage(Package):
    archives = None
    
    def __init__(self):
        super(ArchivePackage, self).__init__()
        
        self.archives = []
    
    def download(self, modpath, files=None):
        total = float(len(self.archives))
        
        for i, (name, path, urls) in self.archives:
            if files is not None and name not in files:
                continue
            
            dest = os.path.join(modpath, name)
            progress.start_task(i / total, 1 / total)
            util.try_download(urls, dest)
            progress.finish_task()
    
    def extract(self, modpath, files=None):
        total = float(len(self.archives))
        
        for i, (name, path, urls) in self.archives:
            if files is not None and name not in files:
                continue
            
            archive = os.path.join(modpath, name)
            if not os.path.isfile(archive):
                logging.error('Archive %s is missing!', archive)
                continue
            
            progress.update(i / total, name)
            dest = os.path.join(modpath, path)
            
            util.extract_archive(archive, dest, True)
            os.unlink(archive)
