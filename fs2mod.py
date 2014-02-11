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

import os
import logging
import tempfile
import zipfile
import subprocess
import shutil
import six
import progress
from fso_parser import ModInfo
from util import download, ipath, pjoin, is_archive, extract_archive

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
    update = None
    version = None
    
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
                if line[0] in ('secondrylist', 'secondarylist', 'primarylist'):
                    deps.extend(filter(lambda x: x != '', line[1].strip(';').split(',')))
        
        self.dependencies = [('lookup', item) for item in deps]

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
                download.append(chksum + ';' + filename + ';' + url[0] + filename)
        
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
        archive.writestr('root/download', '\n'.join(download))
        archive.writestr('root/vp', '\n'.join(vp))
        archive.writestr('root/title', self.name)
        archive.writestr('root/update', 'PLEASE CHANGE')
        archive.writestr('root/dep', ';CHANGEME'.join(self.dependencies))
        archive.writestr('root/version', self.version)
        
        archive.close()
    
    def read_zip(self, zobj, path=None):
        if path is None:
            if isinstance(zobj, six.string_types):
                path = zobj
            else:
                raise RuntimeError('read_zip() expects parameter 1 to be a string or to be passed a name as parameter 2!')
        
        archive = zipfile.ZipFile(zobj, 'r')
        
        # Hellzed's installer ignores paths in downloaded archives, remember this.
        self.ignore_subpath = True
        self.name = archive.open('root/title').read().decode('utf8', 'replace').strip()
        self.update = ('fs2mod', archive.open('root/update').read().decode('utf8', 'replace').strip(), path)
        self.folder = os.path.basename(path).split('.')[0]
        
        dl_names = dict()
        
        for line in archive.open('root/download'):
            line = line.decode('utf8', 'replace').strip().split(';')
            filename = os.path.basename(line[2])
            dl_names[line[1]] = filename
            
            self.urls.append(([os.path.dirname(line[2])], [filename]))
            self.hashes.append(('MD5', filename, line[0]))
        
        for line in archive.open('root/vp'):
            line = line.decode('utf8', 'replace').strip().split(';')
            
            self.contents[line[1]] = {
                'archive': dl_names[line[2]],
                'md5sum': line[0]
            }
        
        try:
            version = archive.open('root/version').read().decode('utf8', 'replace').strip()
        except KeyError:
            version = ''
        
        self.version = version
        
        try:
            deps = archive.open('root/dep')
        except KeyError:
            deps = []
        
        for line in deps:
            line = line.decode('utf8', 'replace').strip().split(';')
            self.dependencies.append(('fs2mod', line[0], line[1]))
    
    def update_info(self):
        if self.update is None:
            return
        elif self.update[0] == 'fs2mod':
            path = None
            try:
                # Don't overwrite the original file.
                with tempfile.NamedTemporaryFile(delete=False) as stream:
                    path = stream.name
                    download(self.update[1], stream)
                
                    stream.seek(0)
                    self.read_zip(stream, self.update[2])
                
                # Download and reading suceeded. Now we can replace the original file.
                shutil.move(path, self.update[2])
            except:
                logging.exception('Failed to update %s!', self.name)
                
                if path is not None and os.path.isfile(path):
                    os.unlink(path)
        else:
            logging.error('Unknown update type "%s"!', self.update[0])
    
    def lookup_deps(self, modlist):
        needed = [self.name]
        provided = dict()
        
        while len(needed) > 0:
            mod = modlist[needed.pop(0)]

            for dep in mod.dependencies:
                if dep[0] == 'mod_name':
                    if dep[1] in modlist:
                        provided['name://' + dep[1]] = dep[1]
                        needed.append(dep[1])
                    else:
                        logging.warning('Dependency "%s" (a mod\'s name) of "%s" wasn\'t found.', dep[1], mod.name)
                    
                    continue
                
                if dep[0] not in ('lookup', 'fs2mod'):
                    logging.warning('Unknown dependency type "%s"! Skipping "%s" of "%s"...', dep[0], dep[1], mod.name)
                    continue
                
                dep_path = (dep[1] + '/mod.ini').lower()
                if not dep_path in provided:
                    for omod in modlist.values():
                        for path in omod.contents:
                            if pjoin(omod.folder, path).lower().startswith(dep_path) and omod.name != mod.name:
                                provided[dep_path] = omod.name
                                needed.append(omod.name)

                                break

                        if dep_path in provided:
                            break

                    if dep_path not in provided:
                        logging.warning('Dependency "%s" of "%s" wasn\'t found!', dep_path, mod.name)
        
        return set(provided.values()) - set([self.name])
    
    def check_files(self, path):
        count = float(len(self.contents))
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
        count = float(len(self.contents))
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
    count = len(mods) # count_modtree(mods)
    
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
