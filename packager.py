import os
import logging
import shutil
import util


class Package(object):
    id = None
    name = None
    version = None
    modfolder = None
    dependencies = None
    chksums = None
    hash_algo = 'md5'
    logo = None
    description = None
    _mod_ini = None
    _repo = None
    _found_path = None
    
    def __init__(self):
        self.subfolders = []
        self.dependencies = []
        self.chksums = []
    
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
        
        for path, chksum in self.chksums:
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
