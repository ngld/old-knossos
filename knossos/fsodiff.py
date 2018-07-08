## Copyright 2017 Knossos authors, see NOTICE file
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

from __future__ import absolute_import, print_function

import sys
import os.path
import tempfile
import shutil
import subprocess
import json
import hashlib

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from knossos import progress, vplib

ADAPTERS = {}


def register(ext):
    def wrapper(cls):
        ADAPTERS[ext] = cls
        return cls

    return wrapper


class SubFile(object):
    _pos = 0

    def __init__(self, handle, length):
        self._handle = handle
        self._length = length
        self._offset = handle.tell()

    def read(self, length=None):
        if length is None or self._pos + length > self._length:
            length = self._length - self._pos

        if length == 0:
            return None

        self._handle.seek(self._offset + self._pos)
        try:
            return self._handle.read(length)
        finally:
            self._pos = self._handle.tell() - self._offset

    def tell(self):
        return self._pos

    def seek(self, pos, mode=os.SEEK_SET):
        if mode == os.SEEK_CUR:
            pos += self._pos
        elif mode == os.SEEK_END:
            pos = self._length - pos

        self._handle.seek(self._offset + pos)
        self._pos = pos

    def close(self):
        self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class ArchiveAdapter(object):

    def __init__(self, handle):
        self._handle = handle
        self._cache = {}
        self._list = None
        self._modified = {}
        self._added = {}
        self._deleted = []

    def filelist(self):
        raise NotImplemented

    def handle(self, fn):
        raise NotImplemented

    def write(self, fn, gen_out=False):
        raise NotImplemented

    def hash(self, fn):
        if fn in self._cache:
            return self._cache[fn]

        h = hashlib.sha256()
        with self.handle(fn) as stream:
            while True:
                chunk = stream.read(16 * h.block_size)
                if not chunk:
                    break

                h.update(chunk)

        self._cache[fn] = h.hexdigest()
        return self._cache[fn]

    def write_file(self, fn, path):
        if not self._list:
            self._list = self.filelist()

        if fn in self._list:
            self._modified[fn] = path
        else:
            self._added[fn] = path

    def delete_file(self, fn):
        self._deleted.append(fn)

    def delete_files(self, l):
        self._deleted.extend(l)


class DirectoryAdapter(ArchiveAdapter):

    def filelist(self):
        files = []

        for sub, dirs, fns in os.walk(self._handle):
            if sub.startswith(self._handle):
                sub = sub[len(self._handle):]

            for name in fns:
                files.append(os.path.join(sub, name))

        return files

    def handle(self, fn):
        return open(os.path.join(self._handle, fn), 'rb')

    def write(self, fn, gen_out=False):
        assert not gen_out

        if not self._list:
            return False

        count = len(self._list) + len(self._added)
        done = 0.0
        for item in self._list:
            progress.update(done / count, 'Processing "%s"...' % item)
            done += 1

            if item in self._modified:
                shutil.copyfile(self._modified[item], os.path.join(fn, item))
            elif item not in self._deleted:
                shutil.copyfile(os.path.join(self._handle, item), os.path.join(fn, item))

        for item, path in self._added.items():
            progress.update(done / count, 'Processing "%s"...' % item)
            done += 1

            shutil.copyfile(path, os.path.join(fn, item))

        return True


@register('7z')
class SevenAdapter(DirectoryAdapter):

    def __init__(self, handle):
        self._tmp = tempfile.TemporaryDirectory()
        super(SevenAdapter, self).__init__(self._tmp)

        arname = getattr(handle, 'name')
        if arname and arname.lower().endswith('.7z'):
            # This is a simple file on disk. We can just run 7z on it.
            subprocess.check_call(['7z', 'x', os.path.abspath(arname)], cwd=self._tmp)
        else:
            # This file is probably packed in an archive. Extract it before running 7z.
            arname = os.path.join(self._tmp, '___.7z')
            with open(arname, 'wb') as stream:
                shutil.copyfileobj(handle, stream)

            subprocess.check_call(['7z', 'x', os.path.abspath(arname)], cwd=self._tmp)
            os.unlink(arname)

    def write(self, fn, gen_out=False):
        if not self._list:
            return False

        if gen_out:
            fd, fn = tempfile.mkstemp(suffix='.7z', dir=fn)
            os.close(fd)

        with tempfile.TemporaryDirectory() as path:
            progress.start_task(0, 0.5)
            super(SevenAdapter, self).write(path)
            progress.finish_task()

            progress.update(0.5, 'Compressing...')
            subprocess.check_call(['7z', 'a', os.path.abspath(fn), '.'], cwd=path)

        if gen_out:
            return fn
        else:
            return True


@register('vp')
class VpAdapter(ArchiveAdapter):

    def __init__(self, handle):
        super(VpAdapter, self).__init__(vplib.VpReader(handle))

    def filelist(self):
        return self._handle.files.keys()

    def handle(self, fn):
        return SubFile(self._handle.open_file(fn), self._handle.files[fn]['size'])

    def write(self, fn, gen_out=False):
        if not self._list:
            return False

        if gen_out:
            fd, fn = tempfile.mkstemp(suffix='.vp', dir=fn)
            os.close(fd)

        ar = vplib.VpWriter(fn)

        for item in self._list:
            if item in self._modified:
                ar.add_file(item, self._modified[item])
            elif item not in self._deleted:
                ar.add_file(item, self.handle(item))

        for item, path in self._added.items():
            ar.add_file(item, path)

        ar.write()

        if gen_out:
            return fn
        else:
            return True


class Differ(object):

    def __init__(self, a, b, parent=None):
        self._a = get_adapter(a)
        self._b = get_adapter(b)

        self.added = set()
        self.deleted = set()
        self.modified = set()

        self.patches = {}
        self.hashes = {}

        if parent:
            self.parent = parent
        else:
            self.parent = self

    def compare_files(self):
        afiles = set(self._a.filelist())
        bfiles = set(self._b.filelist())

        self.added = bfiles - afiles
        self.deleted = afiles - bfiles
        self.modified = set()

        for fn in self.added:
            self.hashes[fn] = self._b.hash(fn)

        for fn in afiles & bfiles:
            bhash = self._b.hash(fn)
            if self._a.hash(fn) != bhash:
                self.modified.add(fn)
                self.hashes[fn] = bhash

                if fn.endswith(('.7z', '.vp')):
                    subdiff = Differ((self._a.handle(fn), fn), (self._b.handle(fn), fn), self.parent)
                    subdiff.compare_files()
                    self.patches[fn] = subdiff

    def write(self, dest):
        with tempfile.TemporaryDirectory() as tmp:
            # Build file index
            refs = {}
            self.index_files(refs)

            # Write files to disk
            count = len(refs.keys())
            for i, (h, (adp, fn)) in enumerate(refs.items()):
                print('%3d / %3d' % (i, count))

                with open(os.path.join(tmp, h), 'wb') as stream:
                    shutil.copyfileobj(adp.handle(fn), stream)

            with open(os.path.join(tmp, 'meta.json'), 'w') as stream:
                json.dump(self.serialize(), stream)

            subprocess.check_call(['7z', 'a', os.path.abspath(dest), '.'], cwd=tmp)

    def index_files(self, refs):
        for fn in self.added:
            h = self._b.hash(fn)
            if h not in refs:
                refs[h] = (self._b, fn)

        for fn in self.modified:
            if fn in self.patches:
                self.patches[fn].index_files(refs)
            else:
                h = self._b.hash(fn)
                if h not in refs:
                    refs[h] = (self._b, fn)

    def serialize(self):
        meta = {
            'added': list(self.added),
            'deleted': list(self.deleted),
            'modified': list(self.modified),
            'hashes': self.hashes,
            'patches': {}
        }

        for fn, diff in self.patches.items():
            meta['patches'][fn] = diff.serialize()

        return meta


class Patcher(object):
    _id = 0

    def __init__(self, ar, out):
        self._ar = get_adapter(ar)
        self._out = out

    def apply_patch(self, patch):
        with tempfile.TemporaryDirectory() as path:
            os.mkdir(os.path.join(path, 'scrap'))
            subprocess.check_call(['7z', 'x', os.path.abspath(patch)], cwd=path)

            with open(os.path.join(path, 'meta.json'), 'r') as stream:
                meta = json.load(stream)

            if not meta:
                raise Exception('Failed to load metadata!')

            self.apply_changes(meta, path)

    def apply_changes(self, meta, path, root=True):
        h = meta['hashes']
        p = meta['patches']

        for item in meta['modified']:
            if item in p:
                subp = Patcher((self._ar.handle(item), item), os.path.join(path, 'scrap'))
                new_item = subp.apply_changes(p[item], path, False)
                if new_item:
                    self._ar.write_file(item, new_item)
            else:
                self._ar.write_file(item, os.path.join(path, h[item]))

        for item in meta['added']:
            self._ar.write_file(item, os.path.join(path, h[item]))

        self._ar.delete_files(meta['deleted'])

        return self._ar.write(self._out, not root)


def get_adapter(path):
    if isinstance(path, tuple):
        handle, fn = path
    elif os.path.isdir(path):
        return DirectoryAdapter(path)
    else:
        fn = path
        handle = open(fn, 'rb')

    _, ext = os.path.splitext(fn)
    if ext[1:] in ADAPTERS:
        return ADAPTERS[ext[1:]](handle)

    raise Exception('Unknown archive type for %s!' % fn)


if __name__ == '__main__':
    import time

    if len(sys.argv) < 5 or sys.argv[1] not in ('diff', 'patch'):
        print('Usage: %s diff <item a> <item b> <patch>' % os.path.basename(__file__))
        print('Usage: %s patch <input> <patch> <out>' % os.path.basename(__file__))
        sys.exit(1)

    if sys.argv[1] == 'diff':
        differ = Differ(sys.argv[2], sys.argv[3])

        start = time.time()
        differ.compare_files()
        diff_time = time.time() - start

        differ.write(sys.argv[4])
        write_time = time.time() - start - diff_time

        print('Done. Comparing took %ds and writing took %ds.' % (round(diff_time, 3), round(write_time, 3)))
    elif sys.argv[1] == 'patch':
        patcher = Patcher(sys.argv[2], sys.argv[4])

        start = time.time()
        patcher.apply_patch(sys.argv[3])

        print('Done. Patching took %ds.' % (round(time.time() - start, 3)))
