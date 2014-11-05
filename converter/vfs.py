## Copyright 2014 fs2mod-py authors, see NOTICE file
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
import sys
import re
import fnmatch

from knossos import util


class VFSError(Exception):
    pass


class Error(Exception):
    pass


class Container(object):
    root = None

    def __init__(self):
        self.root = Directory('[ROOT]')

    def query(self, path):
        path = path.strip('/')
        plist = []

        while path:
            path, part = os.path.split(path)
            plist.append(part)

        item = self.root
        for name in reversed(plist):
            item = item.contents.get(name)
            if not item:
                raise VFSError('No such file or directory')

        return item

    def _split(self, path):
        parent, name = os.path.split(path)
        return self.query(parent), name

    def put_file(self, path, content):
        obj = self.touch(path)
        obj.content = content

    def get_file(self, path):
        return self.query(path).content

    def copy_file(self, src, dst):
        self.put_file(dst, self.get_file(src))

    def get_tree(self, parent=None, tree=None, prefix=''):
        if parent is None:
            parent = self.root

        if tree is None:
            tree = {}

        for item, info in parent.contents.items():
            if item in ('.', '..'):
                continue

            path = util.pjoin(prefix, item)
            if isinstance(info, Directory):
                self.get_tree(info, tree, path)
            else:
                tree[path] = info.content

        return tree

    # os

    def mkdir(self, path):
        parent, name = self._split(path)
        if name in parent.contents:
            raise VFSError('Path already exists!')

        parent.contents[name] = Directory(name, parent)

    def makedirs(self, path):
        p_path = os.path.dirname(path)
        if not self.isdir(p_path):
            self.makedirs(p_path)

        if not self.isdir(path):
            self.mkdir(path)

    def touch(self, path):
        parent, name = self._split(path)
        if name in parent.contents:
            if isinstance(parent.contents[name], Directory):
                raise VFSError('The path points to a directory!')
            else:
                obj = parent.contents[name]
        else:
            obj = parent.contents[name] = File(name, parent)

        return obj

    def unlink(self, path):
        parent, name = self._split(path)
        if isinstance(parent.contents[name], File):
            del parent.contents[name]
        else:
            raise VFSError('The path points to a directory!')

    def rmdir(self, path):
        obj = self.query(path)
        parent = obj.parent

        if isinstance(obj, Directory):
            # There are always the "." and ".." directories.
            if len(obj.contents) > 2:
                raise VFSError('The directory is not empty!')

            del parent.contents[obj.name]
        else:
            raise VFSError('The path points to a file!')

    def rename(self, path_a, path_b):
        parent, name = self._split(path_a)
        
        dest = self.query(os.path.dirname(path_b))
        dest_name = os.path.basename(path_b)
        
        if dest_name in dest.contents:
            raise VFSError('Destination exists!')

        item = parent.contents[name]
        del parent.contents[name]
        dest.contents[dest_name] = item

    def listdir(self, path):
        items = list(self.query(path).contents.keys())
        items.remove('.')
        items.remove('..')
        return items

    def isdir(self, path):
        try:
            return isinstance(self.query(path), Directory)
        except VFSError:
            return False

    def isfile(self, path):
        try:
            return isinstance(self.query(path), File)
        except VFSError:
            return False

    def exists(self, path):
        try:
            self.query(path)
            return True
        except VFSError:
            return False

    lexists = exists

    # glob

    def glob(self, pattern):
        return Globber.glob(self, pattern)

    def iglob(self, pattern):
        return Globber.iglob(self, pattern)

    # shutil
    def copy(self, src, dst, *, follow_symlinks=True):
        return Shutil.copy(self, src, dst, follow_symlinks=follow_symlinks)

    def copytree(self, src, dst, symlinks=False, ignore=None, copy_function=None,
                 ignore_dangling_symlinks=False):
        return Shutil.copytree(self, src, dst, symlinks, ignore, copy_function, ignore_dangling_symlinks)

    def rmtree(self, path, ignore_errors=False, onerror=None):
        return Shutil.rmtree(self, path, ignore_errors, onerror)

    def move(self, src, dst):
        return Shutil.move(self, src, dst)


class Directory(object):
    contents = None
    parent = None
    name = ''

    def __init__(self, name, parent=None):
        self.contents = {
            '.': self,
            '..': parent
        }
        self.name = name
        self.parent = parent


class File(object):
    parent = None
    name = ''
    content = None

    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent


# Adapted (simplified) from /usr/lib/python3.4/glob.py
class Globber(object):

    @classmethod
    def glob(cls, vfs, pathname):
        """Return a list of paths matching a pathname pattern.

        The pattern may contain simple shell-style wildcards a la
        fnmatch. However, unlike fnmatch, filenames starting with a
        dot are special cases that are not matched by '*' and '?'
        patterns.

        """
        return list(cls.iglob(vfs, pathname))

    @classmethod
    def iglob(cls, vfs, pathname):
        """Return an iterator which yields the paths matching a pathname pattern.

        The pattern may contain simple shell-style wildcards a la
        fnmatch. However, unlike fnmatch, filenames starting with a
        dot are special cases that are not matched by '*' and '?'
        patterns.

        """
        if not cls.has_magic(pathname):
            if vfs.exists(pathname):
                yield pathname
            return

        dirname, basename = os.path.split(pathname)
        if not dirname:
            yield from cls.glob1(vfs, None, basename)
            return

        # `os.path.split()` returns the argument itself as a dirname if it is a
        # drive or UNC path.  Prevent an infinite recursion if a drive or UNC path
        # contains magic characters (i.e. r'\\?\C:').
        
        if dirname != pathname and cls.has_magic(dirname):
            dirs = cls.iglob(vfs, dirname)
        else:
            dirs = [dirname]

        if cls.has_magic(basename):
            glob_in_dir = cls.glob1
        else:
            glob_in_dir = cls.glob0

        for dirname in dirs:
            for name in glob_in_dir(vfs, dirname, basename):
                yield os.path.join(dirname, name)

    # These 2 helper functions non-recursively glob inside a literal directory.
    # They return a list of basenames. `glob1` accepts a pattern while `glob0`
    # takes a literal basename (so it only has to check for its existence).

    @classmethod
    def glob1(cls, vfs, dirname, pattern):
        if not dirname:
            dirname = '.'

        try:
            names = vfs.listdir(dirname)
        except VFSError:
            return []

        if not cls._ishidden(pattern):
            names = [x for x in names if not cls._ishidden(x)]
        return fnmatch.filter(names, pattern)

    @classmethod
    def glob0(cls, vfs, dirname, basename):
        if not basename:
            # `os.path.split()` returns an empty basename for paths ending with a
            # directory separator.  'q*x/' should match only directories.
            if vfs.isdir(dirname):
                return [basename]
        else:
            if vfs.exists(os.path.join(dirname, basename)):
                return [basename]

        return []

    magic_check = re.compile('([*?[])')
    magic_check_bytes = re.compile(b'([*?[])')

    @classmethod
    def has_magic(cls, s):
        if isinstance(s, bytes):
            match = cls.magic_check_bytes.search(s)
        else:
            match = cls.magic_check.search(s)

        return match is not None

    def _ishidden(path):
        return path[0] in ('.', b'.'[0])


# Adapted (simplified) from /usr/lib/python3.4/shutil.py
class Shutil(object):

    @classmethod
    def copy(cls, vfs, src, dst, *, follow_symlinks=True):
        """Copy data and mode bits ("cp src dst"). Return the file's destination.

        The destination may be a directory.

        If follow_symlinks is false, symlinks won't be followed. This
        resembles GNU's "cp -P src dst".

        If source and destination are the same file, a SameFileError will be
        raised.

        """
        if vfs.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        vfs.copy_file(src, dst)
        return dst

    def ignore_patterns(*patterns):
        """Function that can be used as copytree() ignore parameter.

        Patterns is a sequence of glob-style patterns
        that are used to exclude files"""
        def _ignore_patterns(path, names):
            ignored_names = []
            for pattern in patterns:
                ignored_names.extend(fnmatch.filter(names, pattern))
            return set(ignored_names)
        return _ignore_patterns

    @classmethod
    def copytree(cls, vfs, src, dst, symlinks=False, ignore=None, copy_function=None,
                 ignore_dangling_symlinks=False):
        """Recursively copy a directory tree.

        The destination directory must not already exist.
        If exception(s) occur, an Error is raised with a list of reasons.

        If the optional symlinks flag is true, symbolic links in the
        source tree result in symbolic links in the destination tree; if
        it is false, the contents of the files pointed to by symbolic
        links are copied. If the file pointed by the symlink doesn't
        exist, an exception will be added in the list of errors raised in
        an Error exception at the end of the copy process.

        You can set the optional ignore_dangling_symlinks flag to true if you
        want to silence this exception. Notice that this has no effect on
        platforms that don't support os.symlink.

        The optional ignore argument is a callable. If given, it
        is called with the `src` parameter, which is the directory
        being visited by copytree(), and `names` which is the list of
        `src` contents, as returned by os.listdir():

            callable(src, names) -> ignored_names

        Since copytree() is called recursively, the callable will be
        called once for each directory that is copied. It returns a
        list of names relative to the `src` directory that should
        not be copied.

        The optional copy_function argument is a callable that will be used
        to copy each file. It will be called with the source path and the
        destination path as arguments. By default, copy2() is used, but any
        function that supports the same signature (like copy()) can be used.

        """
        if copy_function is None:
            copy_function = cls.copy

        names = vfs.listdir(src)
        if ignore is not None:
            ignored_names = ignore(src, names)
        else:
            ignored_names = set()

        vfs.makedirs(dst)
        errors = []
        for name in names:
            if name in ignored_names:
                continue
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            try:
                if vfs.isdir(srcname):
                    cls.copytree(vfs, srcname, dstname, symlinks, ignore, copy_function)
                else:
                    # Will raise a SpecialFileError for unsupported file types
                    copy_function(vfs, srcname, dstname)

            # catch the Error from the recursive copytree so that we can
            # continue with other files
            except Error as err:
                errors.extend(err.args[0])
            except VFSError as why:
                errors.append((srcname, dstname, str(why)))
        
        if errors:
            raise Error(errors)

        return dst

    # version vulnerable to race conditions
    @classmethod
    def rmtree(cls, vfs, path, ignore_errors=False, onerror=None):
        """Recursively delete a directory tree.

        If ignore_errors is set, errors are ignored; otherwise, if onerror
        is set, it is called to handle the error with arguments (func,
        path, exc_info) where func is platform and implementation dependent;
        path is the argument to that function that caused it to fail; and
        exc_info is a tuple returned by sys.exc_info().  If ignore_errors
        is false and onerror is None, an exception is raised.

        """
        if ignore_errors:
            def onerror(*args):
                pass

        elif onerror is None:
            def onerror(*args):
                raise

        names = []
        try:
            names = vfs.listdir(path)
        except VFSError:
            onerror(vfs.listdir, path, sys.exc_info())

        for name in names:
            fullname = os.path.join(path, name)
            if vfs.isdir(fullname):
                cls.rmtree(vfs, fullname, False, onerror)
            else:
                try:
                    vfs.unlink(fullname)
                except VFSError:
                    onerror(vfs.unlink, fullname, sys.exc_info())
        try:
            vfs.rmdir(path)
        except VFSError:
            onerror(vfs.rmdir, path, sys.exc_info())

    def _basename(path):
        # A basename() variant which first strips the trailing slash, if present.
        # Thus we always get the last component of the path, even for directories.
        sep = os.path.sep + (os.path.altsep or '')
        return os.path.basename(path.rstrip(sep))

    @classmethod
    def move(cls, vfs, src, dst):
        """Recursively move a file or directory to another location. This is
        similar to the Unix "mv" command. Return the file or directory's
        destination.

        If the destination is a directory or a symlink to a directory, the source
        is moved inside the directory. The destination path must not already
        exist.

        If the destination already exists but is not a directory, it may be
        overwritten depending on os.rename() semantics.

        If the destination is on our current filesystem, then rename() is used.
        Otherwise, src is copied to the destination and then removed. Symlinks are
        recreated under the new name if os.rename() fails because of cross
        filesystem renames.

        A lot more could be done here...  A look at a mv.c shows a lot of
        the issues this implementation glosses over.

        """
        real_dst = dst
        if vfs.isdir(dst):
            real_dst = os.path.join(dst, cls._basename(src))
            if vfs.exists(real_dst):
                raise Error("Destination path '%s' already exists" % real_dst)
        try:
            vfs.rename(src, real_dst)
        except VFSError:
            if vfs.isdir(src):
                if cls._destinsrc(src, dst):
                    raise Error("Cannot move a directory '%s' into itself '%s'." % (src, dst))
                cls.copytree(vfs, src, real_dst, symlinks=True)
                cls.rmtree(vfs, src)
            else:
                cls.copy(vfs, src, real_dst)
                vfs.unlink(src)
        return real_dst

    def _destinsrc(src, dst):
        if not src.endswith(os.path.sep):
            src += os.path.sep
        if not dst.endswith(os.path.sep):
            dst += os.path.sep
        return dst.startswith(src)
