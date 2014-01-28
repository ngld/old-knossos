import sys
import os
import tempfile
import hashlib
from six.moves import configparser
import patoolib
import six
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

    def read(self, mod, hook=None):
        if not isinstance(mod, ModInfo):
            raise Exception('Invalid argument! Expected ModInfo!')

        # Copy the attributes.
        for attr in mod.__dict__:
            setattr(self, attr, getattr(mod, attr))

        with tempfile.TemporaryDirectory() as tmpdir:
            # Download all archives...
            if hook is not None:
                self.download(tmpdir, progress=lambda bd, fs, fn, cf, fc: hook(100 * (bd/fs + cf) / fc, '(%d/%d) %s' % (cf, fc, fn)))
            else:
                self.download(tmpdir, progress=lambda bd, fs, fn, cf, fc: sys.stdout.write('\r(%d/%d) %s %d%%' % (cf, fc, fn, 100 * (bd/fs + cf) / fc)))
                sys.stdout.write('\n')

            # Now check them...
            if not self.check_hashes(tmpdir):
                return

            # ... and generate our content list.
            for url, files in self.urls:
                for item in files:
                    path = os.path.join(tmpdir, item)
                    if patoolib.util.guess_mime(path)[0] is None:
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
        parser = configparser.ConfigParser()
        parser.read(path)

        if parser.has_option('multimod', 'secondarylist'):
            deps = parser.get('multimod', 'secondarylist', raw=True).strip('; \t').split(',')
        else:
            deps = []

        if parser.has_option('multimod', 'primarylist'):
            deps += parser.get('multimod', 'primarylist', raw=True).strip('; \t').split(',')

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
