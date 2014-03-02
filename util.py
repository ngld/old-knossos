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

import sys
import os
import logging
import shutil
import subprocess
import six
import progress
from six.moves.urllib.request import urlopen, Request
from qt import QtCore


SEVEN_PATH = '7z'
# Copied from http://sourceforge.net/p/sevenzipjbind/code/ci/master/tree/jbinding-java/src/net/sf/sevenzipjbinding/ArchiveFormat.java
# to conform to the FSO Installer.
ARCHIVE_FORMATS = ('zip', 'tar', 'split', 'rar', 'lzma', 'iso', 'hfs', 'gzip', 'gz',
                   'cpio', 'bzip2', 'bz2', '7z', 'z', 'arj', 'cab', 'lzh', 'chm',
                   'nsis', 'deb', 'rpm', 'udf', 'wim', 'xar')
QUIET = False


def call(*args, **kwargs):
    if sys.platform.startswith('win'):
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
    
    return subprocess.call(*args, **kwargs)


def get(link):
    try:
        logging.info('Retrieving "%s"...', link)
        result = urlopen(Request(link, headers={'User-Agent': 'curl/7.22.0'}))
        if six.PY2:
            code = result.getcode()
        else:
            code = result.status

        if code == 200:
            return result
        elif code in (301, 302):
            if six.PY2:
                return get(result.info()['Location'])
            else:
                return get(result.getheader('Location'))
        else:
            return None
    except:
        logging.exception('Failed to load "%s"!', link)

    return None


def download(link, dest):
    try:
        logging.info('Downloading "%s"...', link)
        result = urlopen(Request(link, headers={'User-Agent': 'curl/7.22.0'}))
        if six.PY2:
            if result.getcode() in (301, 302):
                return download(result.info()['Location'], dest)
            elif result.getcode() != 200:
                logging.error('Download of "%s" failed with code %d!', link, result.getcode())
                return False
            
            try:
                size = float(result.info()['Content-Length'])
            except:
                logging.exception('Failed to parse Content-Length header!')
                size = 1024 ** 4 # = 1 TB
        else:
            if result.status in (301, 302):
                return download(result.getheader('Location'), dest)
            elif result.status != 200:
                logging.error('Download of "%s" failed with code %d!', link, result.status)
                return False
            
            try:
                size = float(result.getheader('Content-Length'))
            except:
                logging.exception('Failed to parse Content-Length header!')
                size = 1024 ** 4 # = 1 TB

        start = dest.tell()
        while True:
            chunk = result.read(50 * 1024)  # Read 50KB chunks
            if not chunk:
                break

            dest.write(chunk)

            progress.update((dest.tell() - start) / size, '%s: %d%%' % (os.path.basename(link), 100 * (dest.tell() - start) / size))
    except:
        logging.exception('Failed to load "%s"!', link)
        return False

    return True


# This function will move the contents of src inside dest so that src/a/r/z.dat ends up as dest/a/r/z.dat.
# It will overwrite everything already present in the destination directory!
def movetree(src, dest, ifix=False):
    if ifix:
        dest = ipath(dest)
    
    if not os.path.isdir(dest):
        os.makedirs(dest)

    if ifix:
        siblings = os.listdir(dest)
        l_siblings = [s.lower() for s in siblings]

    for item in os.listdir(src):
        spath = os.path.join(src, item)
        dpath = os.path.join(dest, item)

        if ifix and not os.path.exists(dpath):
            if item.lower() in l_siblings:
                l_item = siblings[l_siblings.index(item.lower())]
                logging.warning('Changing path "%s" to "%s" to avoid case problems...', dpath, os.path.join(dest, l_item))

                dpath = os.path.join(dest, l_item)
            else:
                siblings.append(item)
                l_siblings.append(item.lower())

        if os.path.isdir(spath):
            movetree(spath, dpath)
        else:
            if os.path.exists(dpath):
                os.unlink(dpath)
            
            shutil.move(spath, dpath)


# Actually transforms a given path into a platform-specific one.
def normpath(path):
    return os.path.normcase(path.replace('\\', '/'))


# Try to map a case insensitive path to an existing one.
def ipath(path):
    if os.path.exists(path):
        return path
    
    parent = os.path.dirname(path)
    if not os.path.exists(parent):
        parent = ipath(parent)

        if not os.path.exists(parent):
            # Well, nothing we can do here...
            return path

    siblings = os.listdir(parent)
    l_siblings = [s.lower() for s in siblings]
    
    oitem = item = os.path.basename(path)
    if item.lower() in l_siblings:
        item = siblings[l_siblings.index(item.lower())]
        path = os.path.join(parent, item)
    
    if item != oitem:
        logging.debug('Picking "%s" for "%s".', item, oitem)
    
    return path


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


def test_7z():
    try:
        return call([SEVEN_PATH, '-h'], stdout=subprocess.DEVNULL) == 0
    except:
        logging.exception('Call to 7z failed!')
        return False


def is_archive(path):
    path = path.lower()
    
    for ext in ARCHIVE_FORMATS:
        if path.endswith('.' + ext):
            return True
    
    return False


def extract_archive(archive, outpath, overwrite=False, files=None, _rec=False):
    if '.tar.' in archive and not _rec:
        # This is a file like whatever.tar.gz. We have to call 7z two times for this kind of file:
        # First to get whatever.tar and second to extract that tar archive.
        
        if not extract_archive(archive, os.path.dirname(archive), True, None, True):
            return False
        
        unc_archive = archive.split('.')
        # Remove the .gz or .bz2 or whatever ending...
        unc_archive.pop()
        
        # ... and put it together again.
        unc_archive = '.'.join(unc_archive)
        res = extract_archive(unc_archive, outpath, overwrite, files)
        
        # Cleanup
        os.unlink(unc_archive)
        return res
        
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


class SignalContainer(QtCore.QObject):
    signal = QtCore.Signal(list)


# This wrapper makes sure that the wrapped function is always run in the QT main thread.
def run_in_qt(func):
    signal = SignalContainer()
    
    def dispatcher(*args):
        signal.emit(args)
    
    def listener(params):
        func(*params)
    
    signal.connect(listener)
    
    return dispatcher


def vercmp(a, b):
    a = a.split('.')
    b = b.split('.')
    
    while len(a) > 0 and len(b) > 0:
        cur_a = a.pop(0)
        cur_b = b.pop(0)
        
        if cur_a < cur_b:
            return -1
        elif cur_a > cur_b:
            return 1
    
    if len(a) == 0 and len(b) == 0:
        return 0
    elif len(a) > len(b):
        return 1
    else:
        return -1


def is_number(s):
    try:
        int(s)
        return True
    except TypeError:
        return False
