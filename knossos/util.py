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
import hashlib
import tempfile
import re
import time
import random
import functools
import glob
import shutil
import semantic_version
import requests
import token_bucket
from threading import Condition, Event, Lock
from collections import deque

from .vplib import VpReader
from . import center, progress
from .qt import QtCore

try:
    from PIL import Image
except ImportError:
    Image = None

SEVEN_PATH = '7z'
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
HASH_LOCK = Lock()
_HAS_TAR = None
DL_POOL = None
_DL_CANCEL = Event()
_DL_CANCEL.clear()
SPEED_LIMIT_BUCKET = None
translate = QtCore.QCoreApplication.translate


class BlockingTokenBucket(object):
    def __init__(self, rate):
        self.limiter = None
        self.rate = None

        self.set_rate(rate)

    def set_rate(self, rate):
        self.limiter = token_bucket.Limiter(rate, rate, token_bucket.MemoryStorage())
        self.rate = rate

    def wait_for_consume(self, tokens, cancel_event):
        while tokens > 0:
            # If the number of tokens is more than what is available in the bucket then we would never be able to
            # consume the tokens. This will retrieve the tokens in smaller steps if the number of requested tokens
            # is larger than the available token rate
            consuming = min(tokens, self.rate)

            # Busy waiting is not optimal but our token bucket does not support anything else
            while not self.limiter.consume(b"default", consuming):
                if cancel_event.is_set():
                    return False
                time.sleep(0.01)

            tokens -= consuming

        return True


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
        kwargs.setdefault('stdin', subprocess.DEVNULL)
        kwargs.setdefault('stdout', subprocess.DEVNULL)
        kwargs.setdefault('stderr', subprocess.DEVNULL)

        si = subprocess.STARTUPINFO()
        si.dwFlags = subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE

        kwargs['startupinfo'] = si

    logging.info('Running %s', args[0])
    return subprocess.call(*args, **kwargs)


def Popen(*args, **kwargs):
    if sys.platform.startswith('win') and not center.DEBUG:
        # Provide the called program with proper I/O on Windows.
        kwargs.setdefault('stdin', subprocess.DEVNULL)
        kwargs.setdefault('stdout', subprocess.DEVNULL)
        kwargs.setdefault('stderr', subprocess.DEVNULL)

        si = subprocess.STARTUPINFO()
        si.dwFlags = subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE

        kwargs['startupinfo'] = si

    logging.info('Running %s', args[0])
    return subprocess.Popen(*args, **kwargs)


def check_output(*args, **kwargs):
    if sys.platform.startswith('win'):
        # Provide the called program with proper I/O on Windows.
        kwargs.setdefault('stdin', subprocess.DEVNULL)
        kwargs.setdefault('stderr', subprocess.DEVNULL)

        if not kwargs.get('no_hide'):
            si = subprocess.STARTUPINFO()
            si.dwFlags = subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            kwargs['startupinfo'] = si

    # Remove the no_hide parameter that is irrelevant to subprocess.check_output
    kwargs.pop('no_hide', None)

    kwargs.setdefault('errors', 'surrogateescape')
    kwargs.setdefault('universal_newlines', True)

    logging.info('Running %s', args[0])
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


def get(link, headers=None, random_ua=False, raw=False, timeout=60):
    global HTTP_SESSION

    if random_ua:
        if headers is None:
            headers = {}

        headers['User-Agent'] = get_user_agent(True)

    result = None
    try:
        result = HTTP_SESSION.get(link, headers=headers, timeout=timeout)
        if result.status_code == 304:
            return 304
        elif result.status_code != 200:
            result.raise_for_status()
    except Exception:
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
    except Exception:
        if result is None:
            logging.exception('Failed to load "%s"!', link)
        else:
            logging.error('Failed to load "%s"! (%d %s)', link, result.status_code, result.reason)
        return None

    return result.text


def _limited_request_iter(result, chunk_size):
    iterator = result.iter_content(chunk_size)
    while True:
        if not SPEED_LIMIT_BUCKET.wait_for_consume(chunk_size, _DL_CANCEL):
            return

        try:
            yield next(iterator)
        except StopIteration:
            return


def _get_download_iterator(result, chunk_size):
    if center.settings['download_bandwidth'] < 0.0:
        # There is no bandwidth limit so just use the normal download method
        return result.iter_content(chunk_size)
    else:
        return _limited_request_iter(result, chunk_size)


def _get_download_chunk_size():
    DEFAULT_CHUNK_SIZE = 512 * 1024
    if center.settings['download_bandwidth'] < 0.0:
        # If there is no bandwidth limit then this should work reasonably well
        return DEFAULT_CHUNK_SIZE
    else:
        # If there is a bandwidth limit then for small limits a too large chunk size will make the GUI appear frozen
        # while the chunk is being downloaded. This will make sure that the GUI is updated twice a second
        return min(int(center.settings['download_bandwidth'] / 2), DEFAULT_CHUNK_SIZE)


def download(link, dest, headers=None, random_ua=False, timeout=60, continue_=False, get_etag=False):
    global HTTP_SESSION, DL_POOL, _DL_CANCEL

    if headers is None:
        headers = {}

    if random_ua:
        headers['User-Agent'] = get_user_agent(True)

    if continue_:
        headers['Range'] = 'bytes=%d-' % dest.tell()

    with DL_POOL:
        if _DL_CANCEL.is_set():
            return False

        logging.info('Downloading "%s"...', link)
        start = time.time()

        try:
            result = HTTP_SESSION.get(link, headers=headers, stream=True, timeout=timeout)
        except requests.exceptions.ConnectionError:
            logging.exception('Failed to load "%s"!', link)
            return False

        if result.status_code == 304:
            return 304
        elif result.status_code == 206:
            if not continue_:
                # sectorgame.com/fsfiles/ always returns code 206 which makes this necessary.
                logging.warning('"%s" returned "206 Partial Content", the downloaded file might be incomplete.', link)
        elif result.status_code != 200:
            logging.error('Failed to load "%s"! (%d %s)', link, result.status_code, result.reason)
            return False

        try:
            size = float(result.headers.get('content-length', 0))
        except Exception:
            logging.exception('Failed to parse Content-Length header!')
            size = 1024 ** 4  # = 1 TB

        if result.status_code != 206 or not continue_:
            dest.seek(0)

        try:
            sc = SpeedCalc()
            for chunk in _get_download_iterator(result, _get_download_chunk_size()):
                dest.write(chunk)

                if sc.push(dest.tell()) != -1:
                    if size > 0:
                        by_done = dest.tell()
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
        except Exception:
            logging.exception('Download of "%s" was interrupted!', link)
            return False
        else:
            duration = time.time() - start

            try:
                post(center.API + 'track', data={
                    'event': 'download',
                    'link': link,
                    'time': str(duration)
                })
            except Exception:
                pass

    if get_etag:
        return result.headers.get('etag', True)

    return True


def cancel_downloads():
    global _DL_CANCEL, DL_POOL

    _DL_CANCEL.set()
    start = time.time()

    # Wait for the downloads to actually cancel but don't block longer than 5 seconds.
    # TODO: Figure out a better solution to interrupt downloads.
    while DL_POOL.get_consumed() > 0 and time.time() - start < 5:
        time.sleep(0.2)

    _DL_CANCEL.clear()


# Try to map a case insensitive path to an existing one.
def ipath(path):
    if os.path.exists(path) or path == '':
        return path

    parent, item = os.path.split(path)
    parent = ipath(parent)

    if not os.path.exists(parent):
        # Well, nothing we can do here...
        return os.path.join(parent, item)

    litem = item.lower()
    for s in os.listdir(parent):
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


def gen_hash(path, algo='sha256', use_hash_cache=True):
    global HASH_CACHE

    path = os.path.abspath(path)
    info = os.stat(path)

    if use_hash_cache and algo == 'sha256' and path in HASH_CACHE:
        chksum, mtime = HASH_CACHE[path]
        if mtime == info.st_mtime:
            # logging.debug('Found checksum for %s in cache.', path)
            return algo, chksum

    with HASH_LOCK:
        logging.debug('Calculating checksum for %s...', path)

        h = hashlib.new(algo)
        with open(path, 'rb') as stream:
            while True:
                chunk = stream.read(16 * h.block_size)
                if not chunk:
                    break

                h.update(chunk)

        chksum = h.hexdigest()

    if algo == 'sha256':
        HASH_CACHE[path] = (chksum, info.st_mtime)

    return algo, chksum


def check_hash(value, path, use_hash_cache=True):
    algo, csum = value

    if algo != 'sha256':
        logging.warning("Comparing checksums which aren't sha256! (%s, %s)" % (csum, path))

    _, path_sum = gen_hash(path, algo, use_hash_cache)
    return csum == path_sum


def test_7z():
    global SEVEN_PATH

    try:
        return call([SEVEN_PATH, '-h'], stdout=subprocess.DEVNULL) == 0
    except Exception as exc:
        logging.error('Call to 7z failed! (%s)' % exc)

        if SEVEN_PATH == '7za':
            return False

        try:
            if call(['7za', '-h'], stdout=subprocess.DEVNULL) == 0:
                SEVEN_PATH = '7za'
                return True
            else:
                return False
        except Exception:
            return False


def extract_archive(archive, outpath, overwrite=False, files=None, _rec=False):
    global _HAS_TAR

    if archive.endswith(('.tar.gz', '.tar.xz', '.tar.bz2', '.tgz')):
        if _HAS_TAR is None:
            _HAS_TAR = call(['tar', '--version'], stdout=subprocess.DEVNULL) == 0

        if _HAS_TAR:
            cmd = ['tar', '-xf', archive, '-C', outpath]

            if archive.endswith(('.gz', '.tgz')):
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


def init_ui(ui, win):
    ui.setupUi(win)
    for attr in ui.__dict__:
        setattr(win, attr, getattr(ui, attr))

    return win


def is_number(s):
    try:
        int(s)
        return True
    except (TypeError, ValueError):
        return False


def get_cpuinfo():
    from .third_party import cpuinfo

    try:
        info = cpuinfo.get_cpu_info()
    except Exception:
        logging.exception('Exception in the cpuinfo module!')
        info = None

    return info


def get_user_agent(random_ua=False):
    if random_ua:
        return random.choice(USER_AGENTS[1:])
    else:
        return USER_AGENTS[0]


def human_list(items):
    if not isinstance(items, list):
        items = list(items)

    if len(items) == 0:
        return ''
    elif len(items) == 1:
        return items[0]
    else:
        return ', '.join(items[:-1]) + translate('util.human_list', ' and ') + items[-1]


def is_fs2_retail_directory(path):
    if not os.path.isdir(path):
        path = os.path.dirname(path)

    try:
        for item in os.listdir(path):
            if item.lower() == 'root_fs2.vp':
                return True

    except FileNotFoundError:
        pass

    return False


def extract_vp_file(vp_path, dest_path):
    if not os.path.isdir(dest_path):
        os.makedirs(dest_path)

    vp_reader = VpReader(vp_path)

    fc = float(len(vp_reader.files))
    done = 0
    for path, meta in vp_reader.files.items():
        progress.update(done / fc, path)
        hdl = vp_reader.open_file(path)

        sub_dest = ipath(os.path.join(dest_path, path))
        sub_par = os.path.dirname(sub_dest)

        if not os.path.isdir(sub_par):
            os.makedirs(sub_par)

        with open(sub_dest, 'wb') as dest_hdl:
            remaining = meta['size']
            bufsize = 16 * 1024  # 16 KiB
            while remaining > 0:
                buf = hdl.read(min(remaining, bufsize))
                if not buf:
                    break

                dest_hdl.write(buf)
                remaining -= bufsize

        done += 1


def enable_raven():
    try:
        from raven import Client
    except ImportError:
        logging.exception('Failed to import raven!')
        return False

    import platform
    import ssl

    from raven.transport.threaded_requests import ThreadedRequestsHTTPTransport
    from raven.handlers.logging import SentryHandler

    if hasattr(sys, 'frozen'):
        if sys.platform == 'darwin':
            cacert_path = os.path.join(sys._MEIPASS, '..', 'Resources', 'certifi', 'cacert.pem')
        else:
            cacert_path = os.path.join(sys._MEIPASS, 'certifi', 'cacert.pem')

        from six.moves.urllib.parse import quote as urlquote
        center.SENTRY_DSN += '&ca_certs=' + urlquote(cacert_path)

    center.raven = Client(
        center.SENTRY_DSN,
        release=center.VERSION,
        environment='debug' if center.DEBUG else 'production',
        transport=ThreadedRequestsHTTPTransport,
        auto_log_stacks=True,
        tags={
            'os': sys.platform,
            'os_title': '%s %s' % (platform.system(), platform.version()),
            'openssl': ssl.OPENSSL_VERSION
        }
    )
    center.raven_handler = SentryHandler(center.raven, level=logging.ERROR)
    logging.getLogger().addHandler(center.raven_handler)

    return True


def disable_raven():
    if center.raven_handler:
        logging.getLogger().removeHandler(center.raven_handler)

    center.raven = None
    center.raven_handler = None


def retry_helper(fn, *args, retries=5):
    while retries > 0:
        try:
            return fn(*args)
        except Exception:
            retries -= 1
            if retries == 0:
                raise

            time.sleep(random.randint(0, 2000) / 1000.)


def safe_unlink(path):
    if sys.platform == 'win32':
        return retry_helper(os.unlink, path)
    else:
        return os.unlink(path)


def safe_rename(a, b):
    if sys.platform == 'win32':
        return retry_helper(os.rename, a, b)
    else:
        return os.rename(a, b)


def safe_copy(a, b):
    if sys.platform == 'win32':
        return retry_helper(shutil.copyfile, a, b)
    else:
        return shutil.copyfile(a, b)


def safe_download(url, dest):
    retries = 5

    while retries > 0:
        with open(dest, 'wb') as stream:
            if download(url, stream):
                return True

        retries -= 1

        if retries > 0:
            time.sleep(random.randint(0, 1000) / 1000.)

    logging.error('Failed to download %s to %s!' % (url, dest))
    safe_unlink(dest)
    return False


def _safe_download(url, dest):
    with open(dest, 'wb') as fobj:
        download(url, fobj)


def ensure_tempdir():
    if center.settings['base_path']:
        path = os.path.join(center.settings['base_path'], 'temp')
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except OSError:
                logging.warn('Failed to create temporary directory!')
                return

        tempfile.tempdir = path


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
        version = str(version)

        if version != '*' and not semantic_version.SpecItem.re_spec.match(version) and not version.startswith('~'):
            # Make a spec out of this version
            version = '==' + version

        return Spec(version)


DL_POOL = ResizableSemaphore(10)
HTTP_SESSION.headers['User-Agent'] = get_user_agent()
SPEED_LIMIT_BUCKET = BlockingTokenBucket(3 * 1024 * 1024)

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
    _HAS_TAR = False
