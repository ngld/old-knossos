import os
import logging
import tempfile
import zipfile
import subprocess
import six
import progress
from fso_parser import ModInfo
from util import ipath, is_archive, extract_archive

if six.PY2:
    import py2_compat

try:
    from PIL import Image
except ImportError:
    Image = None

_has_convert = None


def convert_img(path, outfmt):
    global _has_convert

    fd, dest = tempfile.mkstemp('.' + outfmt)
    os.close(fd)
    if Image is not None:
        img = Image.open(path)
        img.save(dest)
        
        return dest
    else:
        if _has_convert is None:
            try:
                subprocess.check_call(['which', 'convert'], stdout=subprocess.DEVNULL)
                _has_convert = True
            except subprocess.CalledProcessError:
                # Well, this failed, too. Is there any other way to convert an image?
                # For now I'll just abort.
                _has_convert = False
                return None
        elif _has_convert is False:
            return None
        
        subprocess.check_call(['convert', path, dest])
        return dest


class ModInfo2(ModInfo):
    contents = None
    dependencies = None
    logo = None

    def __init__(self, values=None):
        super(ModInfo2, self).__init__()

        self.contents = {}
        self.dependencies = []
        
        if values is not None:
            for key, val in values.items():
                if hasattr(self, key):
                    setattr(self, key, val)
        
        self.folder = self.folder.lstrip('/')
    
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
            
            # Now check them...
            if not self.check_hashes(tmpdir):
                logging.warning('Some hashes failed for "%s". Continuing anyway...', mod.name)

            # ... and generate our content list.
            for url, files in self.urls:
                for item in files:
                    path = os.path.join(tmpdir, item)
                    
                    if not is_archive(path):
                        # This is a simple file.
                        self.contents[item] = {
                            'archive': None,
                            'md5sum': self._hash(path)
                        }
                    else:
                        self._inspect_archive(path, item)
    
    def _inspect_archive(self, path, archive_name):
        with tempfile.TemporaryDirectory() as outdir:
            extract_archive(path, outdir)

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
            for line in stream:
                if line.strip() == '[launcher]':
                    break
            
            # Look for the logo and info text
            for line in stream:
                if line.strip() == '[multimod]':
                    break
                
                line = [p.strip(' ;\n\r') for p in line.split('=')]
                if line[0] == 'image255x112':
                    imgpath = os.path.join(os.path.dirname(path), line[1])
                    if os.path.isfile(imgpath):
                        dest = convert_img(imgpath, 'jpg')
                        
                        if dest is not None:
                            with open(dest, 'rb') as img:
                                self.logo = img.read()
                            
                            os.unlink(dest)
                elif line[0] == 'infotext':
                    if self.desc == '':
                        self.desc = line[1]
            
            # Now look for the primarylist and secondarylist lines...
            for line in stream:
                line = [p.strip() for p in line.split('=')]
                if line[0] == 'primarylist' or line[0] == 'secondarylist':
                    deps.extend(filter(lambda x: x != '', line[1].strip(';').split(',')))
        
        self.dependencies = deps

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
        for path, info in self.contents.items():
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
        msgs = []
        
        for item, info in self.contents.items():
            mypath = ipath(os.path.join(path, item))
            fix = False
            if os.path.isfile(mypath):
                progress.update(checked / count, 'Checking "%s"...' % (item))
                
                if self._hash(mypath) == info['md5sum']:
                    success += 1
                else:
                    msgs.append('File "%s" is corrupted. (checksum mismatch)' % (item))
                    fix = True
            else:
                msgs.append('File "%s" is missing.' % (item))
                fix = True
            
            if fix:
                if info['archive'] is None:
                    archives.add(os.path.basename(item))
                else:
                    archives.add(info['archive'])
            
            checked += 1
        
        return archives, success, count, msgs
    
    def remove(self, path, keep_files=None):
        count = len(self.contents)
        checked = 0
        folders = set()
        if keep_files is None:
            keep_files = set()
        else:
            keep_files = set(keep_files)
        
        for item, info in self.contents.items():
            if item not in keep_files:
                mypath = os.path.join(path, item)
                if os.path.isfile(mypath):
                    progress.update(checked / count, 'Removing "%s"...' % (item))
                    logging.info('Deleting "%s"...', os.path.join(path, item))

                    os.unlink(mypath)
                    folders.add(os.path.dirname(mypath))
            else:
                logging.info('Skipping "%s"...', os.path.join(path, item))
            
            checked += 1
        
        # Sort the folders so that the longest path aka deepest folder comes first.
        folders = sorted(folders, key=len, reverse=True)

        for path in folders:
            # Only remove empty folders...
            if os.path.isdir(path) and len(os.listdir(path)) == 0:
                os.rmdir(path)
            else:
                logging.info('Skipped "%s" because it still contains files.', path)


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
            if m.folder == '':
                for item in m.contents:
                    if '/' in item:
                        sm.dependencies.append(item.split('/')[0])
                        break
            else:
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
