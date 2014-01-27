import logging
import os.path
import re
import shutil
import hashlib
import six
from six.moves.urllib.request import urlopen


def get(link):
    try:
        logging.info('Retrieving "%s"...', link)
        result = urlopen(link)
        if result.getcode() == 200:
            return result
        else:
            return None
    except:
        logging.exception('Failed to load "{0}"!'.format(link))

    return None


def normpath(path):
    return os.path.normcase(path.replace('\\', '/'))


class EntryPoint(object):
    # These URLs are taken from the Java installer. (src/com/fsoinstaller/main/FreeSpaceOpenInstaller.java)
    # These point to the root files which contain the latest installer version and links to the mod configs.
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
            return filter(lambda x: x is not None, [get(home + file) for home in cls.HOME_URLS])

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
        return cls.get('version.txt').readlines()[0].strip()

    @classmethod
    def get_basic_config(cls):
        # basic_config.txt contains one mod or installation option per line.
        # It contains all options which should be enabled for the "Basic" installation.

        return [line.strip() for line in cls.get_lines('basic_config.txt')]

    @classmethod
    def get_mods(cls):
        mods = []

        for link in cls.get_lines('filenames.txt'):
            data = get(link.strip())

            if data is None:
                continue
            else:
                mods.extend(ModParser().parse(data.read()))

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
                    if len(mod.files) < 1:
                        logging.error('ModInfo: Failed to add "%s" to "%s" because we have no URLs, yet!', line, mod.name)
                    else:
                        logging.info('ModInfo: Adding "%s" to mod "%s".', line, mod.name)
                        mod.files[-1][1].append(line)
                
                continue

            if line == 'DESC':
                mod.desc = '\n'.join(self._read_until('ENDDESC'))
            elif line == 'FOLDER':
                mod.folder = normpath(self._read())
            elif line == 'DELETE':
                mod.delete.append(normpath(self._read()))
            elif line == 'RENAME':
                mod.rename.append((normpath(self._read()), normpath(self._read())))
            elif line == 'URL':
                mod.urls.append((self._read(), []))
            elif line == 'MULTIURL':
                mod.urls.extend((self._read_until('ENDMULTI'), []))
            elif line == 'HASH':
                line = self._read()
                parts = re.split('\s+', line)
                if len(parts) == 3:
                    mod.hash.append((parts[0], normpath(parts[1]), parts[2]))
                else:
                    mod.hash.append((line, normpath(self._read()), self._read()))
            elif line == 'VERSION':
                mod.version = self._read()
            elif line == 'NOTE':
                mod.note = '\n'.join(self._read_until('ENDNOTE'))
            elif line == 'NAME':
                mod.submods.append(self._parse_sub())
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
    hash = None
    version = ''
    note = ''
    submods = None

    def __init__(self):
        self.delete = []
        self.rename = []
        self.urls = []
        self.hash = []
        self.submods = []
    
    def download(self, dest):
        for urls, files in self.urls:
            if not isinstance(urls, list):
                urls = [urls]
            
            for filename in files:
                data = None
                for link in urls:
                    data = get(link + filename)
                    if data is not None:
                        with open(os.path.join(dest, filename), 'wb') as dl:
                            shutil.copyfileobj(data, dl)
                        
                        break
                
                if data is None:
                    logging.error('Failed to download "%s"!', filename)
    
    def check_hashes(self, path):
        alright = True
        
        for algo, filepath, chksum in self.hash:
            mysum = hashlib.new(algo)
            with open(os.path.join(path, filepath), 'rb') as stream:
                mysum.update(stream.read(10 * 1024))  # Read 10KB chunks
            
            mysum = mysum.hexdigest()
            if mysum != chksum.lower():
                alright = False
                logging.warning('File "%s" has checksum "%s" but should have "%s"! Used algorithm: %s', filepath, mysum, chksum, algo)
        
        return alright
    
    def execute_del(self, path):
        for item in self.delete:
            logging.info('Deleting "%s"...', item)
            
            item = os.path.join(path, item)
            if os.path.isdir(item):
                shutil.rmtree(item)
            else:
                os.unlink(item)
    
    def execute_rename(self, path):
        for src, dest in self.rename:
            logging.info('Moving "%s" to "%s"...', src, dest)
            shutil.move(src, dest)
