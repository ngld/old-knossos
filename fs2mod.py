import os
import logging
import tempfile
import zipfile
import hashlib
import patoolib
import six
import progress
from parser import ModInfo

if six.PY2:
    from py2_compat import TemporaryDirectory as T
    tempfile.TemporaryDirectory = T
    del T


class ModInfo2(ModInfo):
    contents = None
    dependencies = None

    def __init__(self):
        super(ModInfo2, self).__init__()

        self.contents = {}
        self.dependencies = []
    
    # hook(progress, text)
    def read(self, mod, hook=None):
        if not isinstance(mod, ModInfo):
            raise Exception('Invalid argument! Expected ModInfo!')

        # Copy the attributes.
        for attr in mod.__dict__:
            setattr(self, attr, getattr(mod, attr))

        with tempfile.TemporaryDirectory() as tmpdir:
            # Download all archives...
            if hook is not None:
                self.download(tmpdir)
            else:
                self.download(tmpdir)

            # Now check them...
            if not self.check_hashes(tmpdir):
                return
            
            # Add hashes for downloaded files if they have none.
            for urls, files in self.urls:
                for filename in files:
                    found = False
                    for a, path, c in self.hashes:
                        if filename == path:
                            found = True
                            break
                    
                    if not found:
                        self.hashes.append(('MD5', filename, self._hash(os.path.join(tmpdir, filename))))
            
            # ... and generate our content list.
            for url, files in self.urls:
                for item in files:
                    path = os.path.join(tmpdir, item)
                    
                    if not self.is_archive(os.path.join(path, item)):
                        # This is a simple file.
                        self.contents[item] = {
                            'archive': None,
                            'md5sum': self._hash(path)
                        }
                    else:
                        self._inspect_archive(path, item)
    
    def _inspect_archive(self, path, archive_name):
        with tempfile.TemporaryDirectory() as outdir:
            patoolib.extract_archive(path, outdir=outdir)

            for dpath, dirs, files in os.walk(outdir):
                for item in files:
                    # NOTE: I hardcoded a forward slash here so it's the same
                    # on all platforms.
                    fpath = (dpath[len(outdir):] + '/' + item).lstrip('/')
                    self.contents[fpath] = {
                        'archive': archive_name,
                        'md5sum': self._hash(os.path.join(dpath, item))
                    }

                    if item == 'mod.ini':
                        self._inspect_modini(os.path.join(dpath, item))

    def _inspect_modini(self, path):
        deps = []
        with open(path, 'r') as stream:
            # Skip straight to the multimod section...
            for line in stream:
                if line.strip() == '[multimod]':
                    break
            
            # Now look for the primarylist and secondarylist lines...
            for line in stream:
                line = [p.strip() for p in line.split('=')]
                if line[0] == 'primarylist' or line[0] == 'secondarylist':
                    deps.extend(filter(lambda x: x != '', line[1].strip(';').split(',')))
        
        self.dependencies = deps

    def _hash(self, path):
        h = hashlib.md5()
        with open(path, 'rb') as stream:
            while True:
                chunk = stream.read(8 * 1024)
                if not chunk:
                    break

                h.update(chunk)

        return h.hexdigest()
    
    def generate_zip(self, zpath):
        # download file
        download = []
        for url, files in self.urls:
            for filename in files:
                chksum = ''
                for a, name, csum in self.hashes:
                    if name == filename:
                        chksum = csum
                        break
                
                # Just pick the first URL for now...
                download.append(chksum + ';' + filename + ';' + url + filename)
        
        # vp file
        vp = []
        for path, info in self.contents.iteritems():
            if self.folder == '/':
                # Strip the mod folder off.
                
                path = path.split('/')
                path.pop(0)
                path = '/'.join('/')
            
            vp.append(info['md5sum'] + ';' + path + ';' + info['archive'] if info['archive'] is not None else '')
        
        # update and dep files are problematic
        # I have the folders a mod depends on but I can't provide a link to their fs2mod files...
        # I'm just leaving the links out for now...
        
        # Now build the actual archive.
        archive = zipfile.ZipFile(zpath, 'w')
        archive.writestr('download', '\n'.join(download))
        archive.writestr('vp', '\n'.join(vp))
        archive.writestr('title', self.name)
        archive.writestr('update', 'PLEASE CHANGE')
        archive.writestr('dep', ';CHANGEME'.join(self.dependencies))
        archive.close()
    
    def check_files(self, path):
        count = len(self.contents)
        success = 0
        checked = 0
        
        archives = set()
        
        for item, info in self.contents.iteritems():
            mypath = os.path.join(path, item)
            fix = False
            if os.path.isfile(mypath):
                progress.update(checked / count, 'Checking "%s"...' % (item))
                
                if self._hash(mypath) == info['md5sum']:
                    success += 1
                else:
                    logging.warning('File "%s" is corrupted. (checksum mismatch)', item)
                    fix = True
            else:
                logging.warning('File "%s" is missing.', item)
                fix = True
            
            if fix:
                if info['archive'] is None:
                    archives.add(os.path.basename(item))
                else:
                    archives.add(info['archive'])
            
            checked += 1
        
        return archives, success, count


def count_modtree(mods):
    count = 0
    for mod in mods:
        count += count_modtree(mod.submods) + 1
    
    return count


def convert_modtree(mods, complete=0):
    mod2s = []
    count = len(mods)  # count_modtree(mods)
    
    for mod in mods:
        m = ModInfo2()
        progress.start_task(complete / count, 1 / count, 'Converting "%s": %%s' % mod.name)
        m.read(mod)
        progress.finish_task()
        
        mod2s.append(m)
        complete += 1
        
        m.submods = convert_modtree(m.submods, complete)
        for i, sm in enumerate(m.submods):
            sm.dependencies.append(m.folder)
            mod2s.append(sm)
            m.submods[i] = sm.name
    
    return mod2s


def find_mod(mods, needle):
    for mod in mods:
        if mod.name == needle:
            return mod
        
        res = find_mod(mod.submods, needle)
        if res is not None:
            return res
    
    return None


def _resolve_dependencies(deps, modtree):
    d_mods = []
    
    for mod in modtree:
        for item in mod.contents:
            path = mod.folder + '/' + item
            if path in deps:
                deps.remove(path)
                d_mods.append(mod)
                
                if len(deps) == 0:
                    return d_mods
            
        d_mods.extend(_resolve_dependencies(deps, mod.submods))
    
    return d_mods


def resolve_dependencies(mod, modtree):
    return _resolve_dependencies(mod.dependencies[:], modtree)
