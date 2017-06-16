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

from __future__ import absolute_import, print_function, division

import sys
import os
import logging
import subprocess
import struct
import hashlib
import tempfile
import re
import time
import json
import random
import functools
import glob
import semantic_version
import requests
from collections import OrderedDict
from threading import Condition, Event
from collections import deque

from . import center, progress
from .qt import QtCore

try:
    from PIL import Image
except ImportError:
    Image = None

SEVEN_PATH = '7z'
# Copied from http://sourceforge.net/p/sevenzipjbind/code/ci/master/tree/jbinding-java/src/net/sf/sevenzipjbinding/ArchiveFormat.java
# to conform to the FSO Installer.
ARCHIVE_FORMATS = ('zip', 'tar', 'split', 'rar', 'lzma', 'iso', 'hfs', 'gzip', 'gz',
                   'cpio', 'bzip2', 'bz2', '7z', 'z', 'arj', 'cab', 'lzh', 'chm',
                   'nsis', 'deb', 'rpm', 'udf', 'wim', 'xar')
# TODO: Too many?
USER_AGENTS = (
    'Mozilla/5.0 (compatible; Knossos %s +http://dev.tproxy.de/knossos/)' % (center.VERSION),
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/5.0)',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; WOW64; Trident/6.0)',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.78.2 (KHTML, like Gecko) Version/6.1.6 Safari/537.78.2',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0',
    'Mozilla/5.0 (Macintosh; U; PPC Mac OS X; de-de) AppleWebKit/125.2 (KHTML, like Gecko)',
    'Mozilla/5.0 (Windows NT 5.0; rv:21.0) Gecko/20100101 Firefox/21.0',
    'Mozilla/5.0 (Windows NT 5.1; rv:32.0) Gecko/20100101 Firefox/32.0',
    'Mozilla/5.0 (Windows NT 5.1; rv:6.0.2) Gecko/20100101 Firefox/6.0.2',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; rv:32.0.3) Gecko/20100101 Firefox/32.0.3 anonymized by Abelssoft 1108446737',
    'Mozilla/5.0 (Windows NT 6.1; rv:32.0) Gecko/20100101 Firefox/32.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.104 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.4 (KHTML, like Gecko) Chrome/22.0.1229.94 Safari/537.4',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:32.0) Gecko/20100101 Firefox/32.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:33.0) Gecko/20100101 Firefox/33.0',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:32.0) Gecko/20100101 Firefox/32.0',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:29.0) Gecko/20100101 Firefox/29.0 SeaMonkey/2.26.1',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:31.0) Gecko/20100101 Firefox/31.0 DT-Browser/DTB7.031.0020',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:32.0) Gecko/20100101 Firefox/32.0',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:33.0) Gecko/20100101 Firefox/33.0',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; LCJB; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; de-AT; rv:1.7.12)',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.0.10) Gecko/2009042316 Firefox/3.0.10 (.NET CLR 3.5.30729)',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.2.24) Gecko/20111103 Firefox/3.6.24 ( .NET CLR 3.5.30729)',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8 (.NET CLR 3.5.30729)',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:x.x.x) Gecko/20041107 Firefox/x.x',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; pl; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3',
    'Mozilla/5.0 (Windows; U; Windows NT 6.0; de; rv:1.9.2.16) Gecko/20110319 BTRS26718 Firefox/3.6.16 (.NET CLR 3.5.30729)',
    'Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533.4 (KHTML, like Gecko) Iron/5.0.381.0 Chrome/5.0.381 Safari/533.4',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; tr-TR) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27',
    'Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.7 (KHTML, like Gecko) Version/5.0 Safari/534.7',
    'Mozilla/5.0 (X11; Linux i686; rv:21.0) Gecko/20100101 Firefox/21.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2185.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:14.0; ips-agent) Gecko/20100101 Firefox/14.0.1',
    'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:21.0) Gecko/20100101 Firefox/21.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:33.0) Gecko/20100101 Firefox/33.0',
    'Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.10',
    'Opera/9.80 (Windows NT 6.1; WOW64) Presto/2.12.388 Version/12.17'
)
HTTP_SESSION = requests.Session()
HTTP_SESSION.verify = True
QUIET = not center.DEBUG
QUIET_EXC = False
HASH_CACHE = dict()
_HAS_CONVERT = None
_HAS_TAR = None
DL_POOL = None
_DL_CANCEL = Event()
_DL_CANCEL.clear()
translate = QtCore.QCoreApplication.translate


# See code/cmdline/cmdline.cpp (in the SCP source) for details on the data structure.
class FlagsReader(object):
    _stream = None
    easy_flags = None
    flags = None
    build_caps = None

    def __init__(self, stream):
        self._stream = stream
        self.read()

    def unpack(self, fmt):
        if isinstance(fmt, struct.Struct):
            return fmt.unpack(self._stream.read(fmt.size))
        else:
            return struct.unpack(fmt, self._stream.read(struct.calcsize(fmt)))

    def read(self):
        # Explanation of unpack() and Struct() parameters: http://docs.python.org/3/library/struct.html#format-characters
        self.easy_flags = OrderedDict()
        self.flags = OrderedDict()

        easy_size, flag_size = self.unpack('2i')

        easy_struct = struct.Struct('32s')
        flag_struct = struct.Struct('20s40s?ii16s256s')

        if easy_size != easy_struct.size:
            logging.error('EasyFlags size is %d but I expected %d!', easy_size, easy_struct.size)
            return

        if flag_size != flag_struct.size:
            logging.error('Flag size is %d but I expected %d!', flag_size, flag_struct.size)
            return

        for i in range(self.unpack('i')[0]):
            self.easy_flags[1 << i] = self.unpack(easy_struct)[0].decode('utf8').strip('\x00')

        for i in range(self.unpack('i')[0]):
            flag = self.unpack(flag_struct)
            flag = {
                'name': flag[0].decode('utf8').strip('\x00'),
                'desc': flag[1].decode('utf8').strip('\x00'),
                'fso_only': flag[2],
                'on_flags': flag[3],
                'off_flags': flag[4],
                'type': flag[5].decode('utf8').strip('\x00'),
                'web_url': flag[6].decode('utf8').strip('\x00')
            }

            if flag['type'] not in self.flags:
                self.flags[flag['type']] = []

            self.flags[flag['type']].append(flag)

        self.build_caps = self.unpack('b')[0]

    @property
    def openal(self):
        return self.build_caps & 1

    @property
    def no_d3d(self):
        return self.build_caps & (1 << 1)

    @property
    def new_snd(self):
        return self.build_caps & (1 << 2)

    @property
    def sdl(self):
        return self.build_caps & (1 << 3)

    def to_dict(self):
        return {
            'easy_flags': self.easy_flags,
            'flags': self.flags,
            'openal': self.openal,
            'no_d3d': self.no_d3d,
            'new_snd': self.new_snd,
            'sdl': self.sdl
        }


class ResizableSemaphore(object):
    _capacity = 0
    _free = 0
    _cond = None

    def __init__(self, cap):
        self._capacity = cap
        self._free = cap
        self._cond = Condition()

    def acquire(self, blocking=True, timeout=None):
        if not blocking and timeout is not None:
            raise ValueError("can't specify timeout for non-blocking acquire")

        rc = False
        endtime = None
        with self._cond:
            while self._free < 1:
                if not blocking:
                    break
                if timeout is not None:
                    if endtime is None:
                        endtime = time.time() + timeout
                    else:
                        timeout = endtime - time.time()
                        if timeout <= 0:
                            break
                self._cond.wait(timeout)
            else:
                self._free -= 1
                rc = True
        return rc

    def release(self):
        with self._cond:
            if self._free >= self._capacity:
                raise ValueError('Semaphore released too many times')

            self._free += 1
            if self._free > 0:
                self._cond.notify()

    __enter__ = acquire

    def __exit__(self, t, v, tb):
        self.release()

    def get_capacity(self):
        return self._capacity

    def set_capacity(self, cap):
        diff = cap - self._capacity
        with self._cond:
            self._capacity = cap
            self._free += diff

            self._cond.notify_all()

        # logging.debug('Capacity set to %d, was %d. I now have %d free slots.', self._capacity, self._capacity - diff, self._free)

    def get_consumed(self):
        with self._cond:
            return self._capacity - self._free


class SpeedCalc(object):
    speeds = None
    last_time = 0
    last_bytes = 0
    interval = 0.5

    def __init__(self):
        self.speeds = deque(maxlen=30)

    def push(self, bytes):
        now = time.time()

        if self.last_time != 0:
            if (now - self.last_time) < self.interval:
                # Enforce a little gap between two speed measurements.
                return -1

            self.speeds.append(float(bytes - self.last_bytes) / float(now - self.last_time))

        self.last_time = now
        self.last_bytes = bytes

    def get_speed(self):
        if len(self.speeds) == 0:
            return 0.1

        return max(sum(self.speeds) / len(self.speeds), 0.1)


def call(*args, **kwargs):
    if sys.platform.startswith('win') and not center.DEBUG:
        # Provide the called program with proper I/O on Windows.
        if 'stdin' not in kwargs:
            kwargs['stdin'] = subprocess.DEVNULL

        if 'stdout' not in kwargs:
            kwargs['stdout'] = subprocess.DEVNULL

        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.DEVNULL

        si = subprocess.STARTUPINFO()
        si.dwFlags = subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE

        kwargs['startupinfo'] = si

    logging.debug('Running %s', args[0])
    return subprocess.call(*args, **kwargs)


def check_output(*args, **kwargs):
    if sys.platform.startswith('win'):
        # Provide the called program with proper I/O on Windows.
        if 'stdin' not in kwargs:
            kwargs['stdin'] = subprocess.DEVNULL

        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.DEVNULL

        si = subprocess.STARTUPINFO()
        si.dwFlags = subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE

        kwargs['startupinfo'] = si

    if 'universal_newlines' not in kwargs:
        kwargs['universal_newlines'] = True

    logging.debug('Running %s', args[0])
    return subprocess.check_output(*args, **kwargs)


def format_bytes(value):
    unit = 'Bytes'
    if value > 1024:
        value = value / 1024
        unit = 'KB'
    if value > 1024:
        value = value / 1024
        unit = 'MB'
    if value > 1024:
        value = value / 1024
        unit = 'GB'
    if value > 1024:
        value = value / 1024
        unit = 'TB'

    return str(round(value)) + ' ' + unit


def get(link, headers=None, random_ua=False, raw=False):
    global HTTP_SESSION

    if random_ua:
        if headers is None:
            headers = {}

        headers['User-Agent'] = get_user_agent(True)

    result = None
    try:
        result = HTTP_SESSION.get(link, headers=headers)
        if result.status_code == 304:
            return 304
        elif result.status_code != 200:
            result.raise_for_status()
    except:
        if result is None:
            logging.exception('Failed to load "%s"!', link)
        else:
            logging.error('Failed to load "%s"! (%d %s)', link, result.status_code, result.reason)
        return None

    if raw:
        return result
    else:
        return result.text


def post(link, data, headers=None, random_ua=False):
    global HTTP_SESSION

    if random_ua:
        if headers is None:
            headers = {}

        headers['User-Agent'] = get_user_agent(True)

    result = None
    try:
        result = HTTP_SESSION.post(link, data=data, headers=headers)
        if result.status_code != 200:
            result.raise_for_status()
    except:
        if result is None:
            logging.exception('Failed to load "%s"!', link)
        else:
            logging.error('Failed to load "%s"! (%d %s)', link, result.status_code, result.reason)
        return None

    return result.text


def download(link, dest, headers=None, random_ua=False):
    global HTTP_SESSION, DL_POOL, _DL_CANCEL

    if random_ua:
        if headers is None:
            headers = {}

        headers['User-Agent'] = get_user_agent(True)

    with DL_POOL:
        if _DL_CANCEL.is_set():
            return False

        logging.info('Downloading "%s"...', link)

        try:
            result = HTTP_SESSION.get(link, headers=headers, stream=True)
        except requests.exceptions.ConnectionError:
            logging.exception('Failed to load "%s"!', link)
            return False

        if result.status_code == 304:
            return 304
        elif result.status_code == 206:
            # sectorgame.com/fsfiles/ always returns code 206 which makes this necessary.
            logging.warning('"%s" returned "206 Partial Content", the downloaded file might be incomplete.', link)
        elif result.status_code != 200:
            logging.error('Failed to load "%s"! (%d %s)', link, result.status_code, result.reason)
            return False

        try:
            size = float(result.headers.get('content-length', 0))
        except:
            logging.exception('Failed to parse Content-Length header!')
            size = 1024 ** 4  # = 1 TB

        try:
            start = dest.tell()
            sc = SpeedCalc()
            for chunk in result.iter_content(512 * 1024):
                dest.write(chunk)

                if sc.push(dest.tell()) != -1:
                    if size > 0:
                        by_done = dest.tell() - start
                        speed = sc.get_speed()
                        p = by_done / size
                        text = format_bytes(speed) + '/s, '
                        text += time.strftime('%M:%S', time.gmtime((size - by_done) / speed)) + ' left'
                    else:
                        p = 0
                        text = ''
                    progress.update(p, text)

                if _DL_CANCEL.is_set():
                    return False
        except:
            logging.exception('Download of "%s" was interrupted!', link)
            return False

    return True


def cancel_downloads():
    global _DL_CANCEL, DL_POOL

    _DL_CANCEL.set()
    # Wait for the downloads to actually cancel.
    while DL_POOL.get_consumed() > 0:
        time.sleep(0.2)

    _DL_CANCEL.clear()


# Tries all passed links until one succeeds.
def try_download(links, dest):
    for url in links:
        if download(url, dest):
            return True

    return False


# Actually transforms a given path into a platform-specific one.
def normpath(path):
    return os.path.normcase(path.replace('\\', '/'))


# Try to map a case insensitive path to an existing one.
def ipath(path):
    if os.path.exists(path) or path == '':
        return path

    parent, item = os.path.split(path)
    parent = ipath(parent)

    if not os.path.exists(parent):
        # Well, nothing we can do here...
        return path

    siblings = os.listdir(parent)
    litem = item.lower()
    for s in siblings:
        if s.lower() == litem:
            logging.debug('Picking "%s" for "%s".', s, item)
            path = os.path.join(parent, s)
            break

    return path


# TODO: Shouldn't we also handle ./ and ../ here ?
def pjoin(*args):
    path = ''
    for arg in args:
        if arg.startswith('/'):
            path = arg
        elif path == '' or path.endswith('/'):
            path += arg
        else:
            path += '/' + arg

    return path


def url_join(a, b):
    if re.match(r'[a-zA-Z]+://.*', b):
        # A full URL
        return b

    if b == '':
        # Umm....
        return a

    if b[0] == '/':
        if len(b) > 1 and b[1] == '/':
            # The second part begins with // which means we have to grab a's protocol.
            proto = a[:a.find(':')]
            return proto + ':' + b

        # An absolute path
        info = re.match(r'([a-zA-Z]+://[^/]+).*', a)
        return info.group(1) + b

    return pjoin(a, b)


def gen_hash(path, algo='md5'):
    global HASH_CACHE

    path = os.path.abspath(path)
    info = os.stat(path)

    if algo == 'md5' and path in HASH_CACHE:
        chksum, mtime = HASH_CACHE[path]
        if mtime == info.st_mtime:
            # logging.debug('Found checksum for %s in cache.', path)
            return chksum

    logging.debug('Calculating checksum for %s...', path)

    h = hashlib.new(algo)
    with open(path, 'rb') as stream:
        while True:
            chunk = stream.read(16 * h.block_size)
            if not chunk:
                break

            h.update(chunk)

    chksum = h.hexdigest()
    if algo == 'md5':
        HASH_CACHE[path] = (chksum, info.st_mtime)

    return chksum


def test_7z():
    global SEVEN_PATH

    try:
        return call([SEVEN_PATH, '-h'], stdout=subprocess.DEVNULL) == 0
    except:
        logging.exception('Call to 7z failed!')

        if SEVEN_PATH == '7za':
            return False

        try:
            if call(['7za', '-h'], stdout=subprocess.DEVNULL) == 0:
                SEVEN_PATH = '7za'
                return True
            else:
                return False
        except:
            return False


def is_archive(path):
    path = path.lower()

    for ext in ARCHIVE_FORMATS:
        if path.endswith('.' + ext):
            return True

    return False


def extract_archive(archive, outpath, overwrite=False, files=None, _rec=False):
    global _HAS_TAR

    if archive.endswith(('.tar.gz', '.tar.xz', '.tar.bz2', '.tgz')):
        if _HAS_TAR is None:
            _HAS_TAR = call(['tar', '--version'], stdout=subprocess.DEVNULL) == 0

        if _HAS_TAR:
            cmd = ['tar', '-xf', archive, '-C', outpath]

            if archive.endswith('.gz'):
                cmd.append('-z')
            elif archive.endswith('.xz'):
                cmd.append('-J')
            elif archive.endswith('.bz2'):
                cmd.append('-j')

            if overwrite:
                cmd.append('--overwrite')

            if files:
                cmd.extend(files)

            if not os.path.isdir(outpath):
                os.makedirs(outpath)

            if QUIET:
                return call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
            else:
                return call(cmd) == 0

        if not _rec:
            # This is a file like whatever.tar.gz. We have to call 7z two times for this kind of file:
            # First to get whatever.tar and a second time to extract that tar archive.

            if not extract_archive(archive, os.path.dirname(archive), True, None, True):
                return False

            unc_archive = archive.split('.')
            # Remove the .gz or .bz2 or whatever ending...
            if unc_archive.pop() == 'tgz':
                unc_archive.append('tar')

            # ... and put it together again.
            unc_archive = '.'.join(unc_archive)
            res = extract_archive(unc_archive, outpath, overwrite, files, True)

            # Cleanup
            os.unlink(unc_archive)
            return res

    if archive.endswith('.dmg') and not _rec:
        # We have to call 7z twice for this file type. The first time, 7z only extracts the section contained in the file.
        # The second time, 7z extracts the actual contents from the HFS image.

        with tempfile.TemporaryDirectory() as tp:
            if not extract_archive(archive, tp, False, None, True):
                return False

            # Now look for the [0-9].hfs file. It could be that the number is always 3 but I want to be safe.
            image = glob.glob(os.path.join(tp, '*.hfs'))
            if len(image) < 1:
                return False

            # Now extract the image...
            return extract_archive(image[0], outpath, overwrite, files, True)

    cmd = [SEVEN_PATH, 'x', '-o' + outpath]
    if overwrite:
        cmd.append('-y')

    cmd.append(archive)

    if files is not None:
        cmd.extend(files)

    if QUIET:
        return call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    else:
        return call(cmd) == 0


def convert_img(path, outfmt):
    global _HAS_CONVERT

    fd, dest = tempfile.mkstemp('.' + outfmt)
    os.close(fd)
    if Image is not None:
        img = Image.open(path)
        img.save(dest)

        return dest
    else:
        if _HAS_CONVERT is None:
            try:
                subprocess.check_call(['which', 'convert'], stdout=subprocess.DEVNULL)
                _HAS_CONVERT = True
            except subprocess.CalledProcessError:
                # Well, this failed, too. Is there any other way to convert an image?
                # For now I'll just abort.
                _HAS_CONVERT = False
                return None
        elif _HAS_CONVERT is False:
            return None

        subprocess.check_call(['convert', path, dest])
        return dest


def init_ui(ui, win):
    ui.setupUi(win)
    for attr in ui.__dict__:
        setattr(win, attr, getattr(ui, attr))

    return win


def is_number(s):
    try:
        int(s)
        return True
    except TypeError:
        return False


def merge_dicts(a, b):
    for k, v in b.items():
        if k in a and isinstance(v, dict) and isinstance(a[k], dict):
            merge_dicts(a[k], v)
        else:
            a[k] = v

    return a


def get_cpuinfo():
    from .launcher import get_cmd

    # Try the cpuid method first but do so in a seperate process in case it segfaults.
    try:
        info = json.loads(check_output(get_cmd(['--cpuinfo'])).strip())
    except subprocess.CalledProcessError:
        info = None
        logging.exception('The CPUID method failed!')
    except:
        info = None
        logging.exception('Failed to process my CPUID output.')

    if info is None:
        from .third_party import cpuinfo

        try:
            info = cpuinfo.get_cpu_info()
        except:
            logging.exception('Exception in the cpuinfo module!')
            info = None

    return info


def get_user_agent(random_ua=False):
    if random_ua:
        return random.choice(USER_AGENTS[1:])
    else:
        return USER_AGENTS[0]


def str_random(slen):
    s = ''
    for i in range(0, slen):
        s += random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

    return s


def human_list(items):
    if not isinstance(items, list):
        items = list(items)

    if len(items) == 0:
        return ''
    elif len(items) == 1:
        return items[0]
    else:
        return ', '.join(items[:-1]) + translate('util.human_list', ' and ') + items[-1]


def connect(sig, cb, *args):
    cb = functools.partial(cb, *args)
    if not hasattr(sig, '_pyl'):
        sig._pyl = []

    sig._pyl.append(cb)
    sig.connect(cb)


class Spec(semantic_version.Spec):

    @classmethod
    def parse(self, specs_string):
        spec_texts = specs_string.split(',')
        res = []

        for spec_text in spec_texts:
            if '-' not in spec_text and '+' not in spec_text and spec_text != '*':
                spec_text = spec_text.split('.')
                while len(spec_text) < 3:
                    spec_text.append('0')

                spec_text = '.'.join(spec_text) + '-'

            res.append(semantic_version.SpecItem(spec_text))

        return tuple(res)

    @staticmethod
    def from_version(version, op='=='):
        return Spec('==' + str(version))


DL_POOL = ResizableSemaphore(10)
HTTP_SESSION.headers['User-Agent'] = get_user_agent()

if not center.DEBUG:
    logging.getLogger('requests.packages.urllib3.connectionpool').propagate = False

if sys.hexversion >= 0x020709F0:
    # In Python 2.7.9 the ssl module from Python 3.x was backported which means we can get rid of
    # the pyOpenSSL monkeypatch in urllib3.
    # On MacOS pyOpenSSL should be avoided at all cost since it's linked (by default) against
    # the system OpenSSL which is *very* old and doesn't support newer features like TLSv1.2.
    # NOTE: It might be better to check ssl.OPENSSL_VERSION
    # See also https://www.python.org/dev/peps/pep-0466/

    if 'requests.packages.urllib3.contrib.pyopenssl' in sys.modules:
        logging.info('Deactivating pyOpenSSL...')
        import requests.packages.urllib3.contrib.pyopenssl as pssl

        pssl.extract_from_urllib3()
        del pssl

if sys.platform.startswith('win'):
    _HAS_CONVERT = False
    _HAS_TAR = False
