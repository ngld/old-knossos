import logging
import os.path
import re
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
			return filter([get(home + file) for home in cls.HOME_URLS], lambda x: x is not None)

	@classmethod
	def get_lines(cls, file):
		lines = set()
		for result in cls.get(file, False):
			lines += result.readlines()
			result.close()

		return lines

	@classmethod
	def get_version(cls):
		# version.txt contains 2 lines: The version and the link to the installer's jar.
		return cls.get('version.txt').readlines()[0]

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
				mods.append(ModParser().parse(data.read()))

		return mods

class Parser(object):
	_data = None

	def _read(self):
		return self._data.pop(0).strip()

	def _read_until(self, data, end):
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
		while True:
			line = self._read()

			if line == 'NAME':
				mods.append(self._parse_sub())
			elif line in self.TOKENS:
				logging.error('ModInfo: Found invalid token "%s" outside a mod!', line)
				return
			elif len(data) == 0:
				logging.error('ModInfo: No mod found!')
				return

		return mods

	def _parse_sub(self):
		mod = ModInfo()
		mod.name = self._read()
		logging.info('ModInfo: Parsing "%s" mod...', mod.name)

		while len(self._data) > 0:
			line = self._read()

			if line not in self.TOKENS:
				logging.warning('ModInfo: Unexpected line "%s". Was expecting a token (%s).', line, ', '.join(self.TOKENS))
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
				mod.urls.append(self._read())
			elif line == 'MULTIURL':
				mod.urls.extend(self._read_until('ENDMULTI'))
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