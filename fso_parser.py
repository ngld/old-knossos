import logging
import os
import re
import shutil
import tempfile
import hashlib
import six
import progress
from util import get, download, normpath, movetree, ipath, is_archive, extract_archive

if six.PY2:
    import py2_compat

HASH_CACHE = dict()


class EntryPoint(object):
    # These URLs are taken from the Java installer.
    # (in src/com/fsoinstaller/main/FreeSpaceOpenInstaller.java)
    # These point to the root files which contain the latest installer version
    # and links to the mod configs.
    HOME_URLS = ('http://www.fsoinstaller.com/files/installer/java/', 'http://scp.indiegames.us/fsoinstaller/')

    # Home files:
    # * version.txt
    # * filenames.txt
    # * basic_config.txt
    @classmethod
    def get(cls, file, use_first=True):
        if use_first:
            for home in cls.HOME_URLS:
                result = get(home + file)
                if result is not None:
                    return result

            return None
        else:
            results = []
            for home in cls.HOME_URLS:
                result = get(home + file)
                if result is not None:
                    results.append(result)

            return results

    @classmethod
    def get_lines(cls, file):
        lines = set()
        for result in cls.get(file, False):
            lines |= set(result.readlines())
            result.close()

        return lines

    @classmethod
    def get_version(cls):
        # version.txt contains 2 lines: The version and the link to the installer's jar.
        return cls.get('version.txt').readlines()[0].decode('utf8').strip()

    @classmethod
    def get_basic_config(cls):
        # basic_config.txt contains one mod or installation option per line.
        # It contains all options which should be enabled for the "Basic" installation.

        return [line.decode('utf8').strip() for line in cls.get_lines('basic_config.txt')]

    @classmethod
    def get_mods(cls):
        mods = []

        for link in cls.get_lines('filenames.txt'):
            data = get(link.decode('utf8').strip())

            if data is None:
                continue
            else:
                mods.extend(ModParser().parse(data.read().decode('utf8')))

        return mods


class Parser(object):
    _data = None

    def _read(self):
        return self._data.pop(0).strip()

    def _read_until(self, end):
        res = []
        while True:
            line = self._read()
            if line == end:
                break
            else:
                res.append(line)

        return res


class ModParser(Parser):
    TOKENS = ('NAME', 'DESC', 'FOLDER', 'DELETE', 'RENAME', 'URL', 'MULTIURL', 'HASH', 'VERSION', 'NOTE', 'END')
    #ENDTOKENS = { 'DESC': 'ENDDESC', 'MULTIURL': 'ENDMULTI', 'NOTE': 'ENDNOTE' }

    def parse(self, data, toplevel=True):
        if isinstance(data, six.string_types):
            data = data.split('\n')

        self._data = data
        mods = []

        # Look for NAME
        while len(self._data) > 0:
            line = self._read()

            if line == 'NAME':
                mods.append(self._parse_sub())
            elif line in self.TOKENS:
                logging.error('ModInfo: Found invalid token "%s" outside a mod!', line)
                return

        if len(mods) < 1:
            logging.error('ModInfo: No mod found!')

        return mods

    def _parse_sub(self):
        mod = ModInfo()
        mod.name = self._read()
        logging.debug('ModInfo: Parsing "%s" mod...', mod.name)

        while len(self._data) > 0:
            line = self._read()

            if line == '':
                continue

            if line not in self.TOKENS:
                if re.match('^[A-Z]+$', line):
                    logging.warning('ModInfo: Unexpected line "%s". Was expecting a token (%s).', line, ', '.join(self.TOKENS))
                else:
                    if len(mod.urls) < 1:
                        logging.error('ModInfo: Failed to add "%s" to "%s" because we have no URLs, yet!', line, mod.name)
                    else:
                        logging.debug('ModInfo: Adding "%s" to mod "%s".', line, mod.name)
                        mod.urls[-1][1].append(line)

                continue

            if line == 'DESC':
                mod.desc = '\n'.join(self._read_until('ENDDESC'))
            elif line == 'FOLDER':
                mod.folder = normpath(self._read())
                if mod.folder == '/':
                    mod.folder = ''
            elif line == 'DELETE':
                mod.delete.append(normpath(self._read()))
            elif line == 'RENAME':
                mod.rename.append((normpath(self._read()), normpath(self._read())))
            elif line == 'URL':
                mod.urls.append(([self._read()], []))
            elif line == 'MULTIURL':
                mod.urls.extend((self._read_until('ENDMULTI'), []))
            elif line == 'HASH':
                line = self._read()
                parts = re.split('\s+', line)
                if len(parts) == 3:
                    mod.hashes.append((parts[0], normpath(parts[1]), parts[2]))
                else:
                    mod.hashes.append((line, normpath(self._read()), self._read()))
            elif line == 'VERSION':
                mod.version = self._read()
            elif line == 'NOTE':
                mod.note = '\n'.join(self._read_until('ENDNOTE'))
            elif line == 'NAME':
                sub = self._parse_sub()
                sub.parent = mod
                mod.submods.append(sub)
            elif line == 'END':
                break
            else:
                logging.warning('ModInfo: Ignoring token "%s" because it wasn\'t implemented!', line)

        return mod


class ModInfo(object):
    name = ''
    desc = ''
    folder = ''
    delete = None
    rename = None
    urls = None
    hashes = None
    version = ''
    note = ''
    submods = None
    parent = None

    def __init__(self):
        self.delete = []
        self.rename = []
        self.urls = []
        self.hashes = []
        self.submods = []

    def _hash(self, path, algo='md5'):
        global HASH_CACHE
        
        path = os.path.abspath(path)
        info = os.stat(path)

        if algo == 'md5' and path in HASH_CACHE:
            chksum, mtime = HASH_CACHE[path]
            if mtime == info.st_mtime:
                return chksum
        
        h = hashlib.new(algo)
        with open(path, 'rb') as stream:
            while True:
                chunk = stream.read(8 * 1024)
                if not chunk:
                    break

                h.update(chunk)

        chksum = h.hexdigest()
        if algo == 'md5':
            HASH_CACHE[path] = (chksum, info.st_mtime)
        
        return chksum
    
    def download(self, dest, sel_files=None):
        count = 0
        num = 0
        for u, files in self.urls:
            if sel_files is not None:
                files = set(files) & sel_files
            count += len(files)

        for urls, files in self.urls:
            if not isinstance(urls, list):
                urls = [urls]

            if sel_files is not None:
                files = set(files) & sel_files

            for filename in files:
                done = False

                for link in urls:
                    with open(os.path.join(dest, filename), 'wb') as dl:
                        progress.start_task(float(num) / count, 1.0 / count, '%d/%d: %%s' % (num + 1, count))
                        if download(link + filename, dl):
                            num += 1
                            done = True
                            progress.finish_task()
                            break
                        
                        progress.finish_task()

                if not done:
                    logging.error('Failed to download "%s"!', filename)
    
    def check_hashes(self, path):
        alright = True

        for algo, filepath, chksum in self.hashes:
            try:
                mysum = self._hash(ipath(os.path.join(path, filepath)), algo)
            except:
                logging.exception('Failed to computed checksum for "%s" with algorithm "%s"!', filepath, algo)
                continue
            
            if mysum != chksum.lower():
                alright = False
                logging.warning('File "%s" has checksum "%s" but should have "%s"! Used algorithm: %s', filepath, mysum, chksum, algo)

        return alright

    def execute_del(self, path):
        count = float(len(self.delete))
        
        for i, item in enumerate(self.delete):
            logging.info('Deleting "%s"...', item)
            progress.update(i / count, 'Deleting "%s"...' % item)

            item = os.path.join(path, item)
            if os.path.isdir(item):
                shutil.rmtree(item)
            elif os.path.exists(item):
                os.unlink(item)
            else:
                logging.warning('"%s" not found!', item)

    def execute_rename(self, path):
        count = float(len(self.rename))
        i = 0
        
        for src, dest in self.rename:
            logging.info('Moving "%s" to "%s"...', src, dest)
            progress.update(i / count, 'Moving "%s" to "%s"...' % (src, dest))
            
            if os.path.exists(src):
                shutil.move(src, dest)
            else:
                logging.warning('"%s" not found!', src)
            i += 1

    def extract(self, path, sel_files=None):
        count = 0.0
        for u, files in self.urls:
            if sel_files is not None:
                files = set(files) & sel_files

            count += len(files)
        
        i = 0
        for u, files in self.urls:
            if sel_files is not None:
                files = set(files) & sel_files

            for item in files:
                mypath = os.path.join(path, item)
                if os.path.exists(mypath) and is_archive(mypath):
                    progress.update(i / count, 'Extracting "%s"...' % item)
                    
                    with tempfile.TemporaryDirectory() as tempdir:
                        # Extract to a temporary directory and then move the result
                        # to final destination to avoid "Do you want to overwrite?" questions.
                        
                        extract_archive(mypath, tempdir)
                        movetree(tempdir, path, ifix=True)
                
                i += 1
    
    def cleanup(self, path, sel_files=None):
        count = 0.0
        for u, files in self.urls:
            if sel_files is not None:
                files = set(files) & sel_files

            count += len(files)
        
        i = 0
        for u, files in self.urls:
            if sel_files is not None:
                files = set(files) & sel_files

            for item in files:
                mypath = os.path.join(path, item)
                if os.path.exists(mypath) and is_archive(mypath):
                    # Only remove the archives...
                    progress.update(i / count, 'Removing "%s"...' % item)
                    os.unlink(mypath)
                
                i += 1

    def setup(self, fs2_path):
        modpath = os.path.join(fs2_path, self.folder)

        if not os.path.isdir(modpath):
            os.mkdir(modpath)
        
        progress.start_task(0, 1/6.0, 'Downloading: %s')
        self.execute_del(modpath)
        progress.finish_task()
        
        progress.start_task(1/6.0, 1/6.0)
        self.execute_rename(modpath)
        progress.finish_task()
        
        progress.start_task(2/6.0, 1/6.0)
        self.download(modpath)
        progress.finish_task()
        
        progress.start_task(3/6.0, 1/6.0)
        self.extract(modpath)
        progress.finish_task()
        
        progress.start_task(4/6.0, 1/6.0)
        self.check_hashes(modpath)
        progress.finish_task()
        
        progress.start_task(5/6.0, 1/6.0)
        self.cleanup(modpath)
        progress.finish_task()
