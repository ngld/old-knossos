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

from __future__ import print_function

import struct
import os
import logging
import shutil

from time import time

from knossos import progress
# See also: http://docs.python.org/library/struct.html#format-characters


class EmptyFileException(Exception):
    def __init__(self, fn):
        self.file = fn


class DataReader(object):
    _file = None
    _size = 0
    failed = False

    def __init__(self, filename):
        if isinstance(filename, str):
            self._file = open(filename, 'rb')
        else:
            self._file = filename

        self._file.seek(0, os.SEEK_END)
        self._size = self._file.tell()
        self._file.seek(0)

        self.read()

    def unpack(self, fmt):
        fmt = '<' + fmt
        try:
            size = struct.calcsize(fmt)
        except MemoryError:
            logging.error('Can\'t read data! Format: {0} [Memory]'.format(fmt))
            raise

        data = self._file.read(size)
        if len(data) < size:
            if hasattr(self._file, 'name'):
                name = self._file.name
            else:
                name = '<stream>'
            logging.error('File "{0}" is too short! Couldn\'t read "{1}". Position: {2}'.format(name, fmt, self._file.tell()))

        data = struct.unpack(fmt, data)

        if len(fmt) == 2:
            return data[0]
        else:
            return data

    def unpack_string(self):
        length = self.unpack('i')
        return self.unpack(str(length) + 's')[0].decode('utf8').rstrip('\x00')


class DataWriter(object):
    _file = None

    def __init__(self, filename):
        if isinstance(filename, str):
            self._file = open(filename, 'wb')
        else:
            self._file = filename

    def pack(self, fmt, *values):
        fmt = '<' + fmt
        self._file.write(struct.pack(fmt, *values))

    def pack_string(self, value):
        value += '\x00'
        length = len(value)

        self.pack('i', length)
        self.pack(str(length) + 's', value)


class VpReader(DataReader):
    fs = None
    files = None

    def cut_str(self, string):
        length = string.find(b'\x00')
        if length == -1:
            return string

        return string[:length]

    def read(self):
        header, version, diroffset, direntries = self.unpack('4siii')

        if header != b'VPVP':
            logging.error('Invalid VP file!')
            self._file.close()
            return

        dirs = 0
        files = 0

        self._file.seek(diroffset)
        self.files = {}
        cur_path = []
        for n in range(direntries):
            offset, size, name, timestamp = self.unpack('ii32si')
            name = self.cut_str(name).decode('utf8').lower()

            if timestamp == 0:
                if size != 0:
                    logging.error('Invalid directory entry "{0}"!'.format(name))
                    continue

                if name == '..':
                    cur_path.pop()
                else:
                    cur_path.append(name)
                    dirs += 1
            else:
                cur_path.append(name)
                self.files['/'.join(cur_path)] = {
                    'offset': offset,
                    'size': size,
                    'timestamp': timestamp
                }
                cur_path.pop()
                files += 1

        logging.info('Found {0} files and {1} directories in "{2}".'.format(files, dirs, self._file.name))

    def open_file(self, path):
        self._file.seek(self.files[path]['offset'])
        return self._file


class VpWriter(DataWriter):
    _files = None
    _count = 0
    _written = 0

    def __init__(self, path):
        super(VpWriter, self).__init__(path)

        self._files = dict()

    def add_file(self, path, content):
        path = path.replace('\\', '/').split('/')
        name = path.pop()
        lvl = self._files

        while len(path) > 0:
            lvl = lvl.setdefault(path.pop(0), {})

        lvl[name] = ('file', content)
        self._count += 1

    def get_file_count(self):
        return self._count

    def write_file(self, name, content, toc):
        progress.update(self._written / float(self._count), 'Packing "%s"...' % name)
        self._written += 1

        if isinstance(content, str):
            content = open(content, 'rb')
            opened = True
        else:
            opened = False

        offset = self._file.tell()
        shutil.copyfileobj(content, self._file)
        size = self._file.tell() - offset

        if size == 0:
            raise EmptyFileException(content)

        if opened:
            content.close()

        toc.append({
            'name': name,
            'offset': offset,
            'size': size,
            'timestamp': int(time())
        })

    def write_dir(self, lvl, toc):
        for name, content in lvl.items():
            if isinstance(content, tuple) and content[0] == 'file':
                # a file
                self.write_file(name, content[1], toc)
            else:
                toc.append({
                    'name': name,
                    'offset': 0,
                    'size': 0,
                    'timestamp': 0
                })
                self.write_dir(content, toc)
                toc.append({
                    'name': '..',
                    'offset': 0,
                    'size': 0,
                    'timestamp': 0
                })

    def write(self):
        self.pack('4siii', b'VPVP', 0, 0, 0)

        toc = []
        self.write_dir(self._files, toc)

        diroffset = self._file.tell()
        dirs = 0
        files = 0

        progress.update(0.99, 'Writing TOC...')
        for item in toc:
            self.pack('ii32si', item['offset'], item['size'], item['name'].encode('utf8'), item['timestamp'])

            if item['timestamp'] == 0:
                dirs += 1
            else:
                files += 1

        self._file.seek(0)
        self.pack('4siii', b'VPVP', 2, diroffset, len(toc))
        self._file.close()

        logging.info('Wrote {0} files and {1} directories in "{2}".'.format(files, dirs, self._file.name))
