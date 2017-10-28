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

import sys
import os.path
import ctypes.util
import re

from subprocess import check_call, CalledProcessError
from fnmatch import translate as fntranslate

DEVNULL = os.open(os.devnull, os.O_RDWR)

if not hasattr(__builtins__, 'FileNotFoundError'):
    class FileNotFoundError(Exception):
        pass


def silent_check(*args, **kwargs):
    kwargs['stdout'] = DEVNULL
    kwargs['stderr'] = DEVNULL

    return check_call(*args, **kwargs)


# BEGIN Python < 3.3 compat
def which(cmd):
    # Check that a given file can be accessed with the correct mode.
    # Additionally check that `file` is not a directory, as on Windows
    # directories pass the os.access check.
    def _access_check(fn):
        return (os.path.exists(fn) and os.access(fn, os.F_OK | os.X_OK)
                and not os.path.isdir(fn))

    # If we're given a path with a directory part, look it up directly rather
    # than referring to PATH directories. This includes checking relative to the
    # current directory, e.g. ./script
    if os.path.dirname(cmd):
        if _access_check(cmd):
            return cmd
        return None

    path = os.environ.get("PATH", os.defpath).split(os.pathsep)

    if sys.platform == "win32":
        # The current directory takes precedence on Windows.
        if os.curdir not in path:
            path.insert(0, os.curdir)

        # PATHEXT is necessary to check on Windows.
        pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
        # See if the given file matches any of the expected path extensions.
        # This will allow us to short circuit when given "python.exe".
        # If it does match, only test that one, otherwise we have to try
        # others.
        if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
            files = [cmd]
        else:
            files = [cmd + ext for ext in pathext]
    else:
        # On other platforms you don't have things like PATHEXT to tell you
        # what file suffixes are executable, so just pass on cmd as-is.
        files = [cmd]

    seen = set()
    for dir in path:
        normdir = os.path.normcase(dir)
        if normdir not in seen:
            seen.add(normdir)
            for thefile in files:
                name = os.path.join(dir, thefile)
                if _access_check(name):
                    return name
    return None

# END Python < 3.3 compat


def build_file_list(path, exts=None):
    if exts:
        ext_filter = re.compile('(%s)' % '|'.join([fntranslate(e) for e in exts]))
        match = ext_filter.match
    else:
        def match(_):
            return True

    result = []
    for path, dirs, files in os.walk(path):
        for name in files:
            if match(name):
                result.append(os.path.join(path, name))

    return result


# based on https://stackoverflow.com/a/29215357
def escape_for_cmd_exe(arg):
    # Escape an argument string to be suitable to be passed to
    # cmd.exe on Windows
    #
    # This method takes an argument that is expected to already be properly
    # escaped for the receiving program to be properly parsed. This argument
    # will be further escaped to pass the interpolation performed by cmd.exe
    # unchanged.
    #
    # Any meta-characters will be escaped, removing the ability to e.g. use
    # redirects or variables.
    #
    # @param arg [String] a single command line argument to escape for cmd.exe
    # @return [String] an escaped string suitable to be passed as a program
    #   argument to cmd.exe

    return re.sub(r'[\(\)\%\!\^"\<\>\&\|]', r'^\g<0>', arg)


_find_unsafe = re.compile(r'[^a-zA-Z0-9_^@%+=:,./-]').search


def quote(s):
    """Return a shell-escaped version of the string *s*."""
    if sys.platform == 'win32':
        if not s or re.search(r'(["\s])', s):
            s = '"' + s.replace('"', r'\"') + '"'

        return s

    if not s:
        return "''"

    if _find_unsafe(s) is None or s in ('$in', '$out'):
        return s

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"


def info(msg):
    """Print an info message"""
    sys.stdout.write(msg)


def fail(msg, required=True):
    """Print an error message and exit"""
    sys.stdout.write(' ' + msg + '\n')

    if required:
        sys.exit(1)


def cmd2str(cmd):
    """Convert a command list into a string with proper escaping."""
    return ' '.join([quote(p) for p in cmd])


def py_script(path, args=[]):
    """Generate a command which executes the passed python script with the
    current interpreter and the given parameters."""
    return cmd2str([sys.executable, os.path.abspath(path)] + args)


def cmdenv(cmd, env):
    """Prefix the given command with the platform specific instructions to set
    the passed environment variables."""

    if isinstance(cmd, list):
        cmd = cmd2str(cmd)

    prefix = ''
    if sys.platform == 'win32':
        prefix = 'cmd /C "'
        cmd += '"'

        for n, v in env.items():
            prefix += 'set %s && ' % quote('%s=%s' % (n, v))
    else:
        for n, v in env.items():
            prefix += '%s=%s ' % (n, quote(str(v)))

    return prefix + cmd


def check_module(mod, required=True):
    info('Checking %s...' % mod)

    try:
        __import__(mod)
    except ImportError:
        fail('Not found!', required)
        return False
    else:
        info(' ok\n')
        return True


def try_program(cmds, name, msg='Looking for %s...', test_param='--version', required=True):
    """Try the given commands and return the first one that works. Return None if none of them work."""
    info(msg % name)
    for cmd in cmds:
        try:
            silent_check(cmd + [test_param])
        except (CalledProcessError, FileNotFoundError):
            pass
        else:
            info(' ' + ' '.join(cmd) + '\n')
            return cmd

    fail('not found!', required)
    return None


def find_program(cmds, name, msg='Looking for %s...', required=True):
    """Look for the given command names in the PATH and return the first find. Returns None if no name could be found."""
    info(msg % name)
    for cmd in cmds:
        path = which(cmd)
        if path:
            info(' %s\n' % path)
            return path

    fail('not found!', required)
    return None


def check_ctypes_lib(names, msg):
    """Try to each passed name and return the first loadable one. None if no name could be loaded."""
    info('Checking for %s...' % msg)

    for lib in names:
        if '.' not in lib:
            lib = ctypes.util.find_library(lib)
            if not lib:
                continue

        try:
            ctypes.cdll.LoadLibrary(lib)
        except Exception as e:
            continue

        info(' %s\n' % lib)
        return lib

    fail('Could not find %r!' % names)
    return None


def build_targets(n, files, rule, new_ext, new_path):
    """Generate build blocks for the given files by replacing their extensions with *new_ext* and placing the new files in *new_path*."""
    names = []

    for fn in files:
        name = os.path.basename(fn)
        dot = name.rfind('.')
        new_name = os.path.join(new_path, name[:dot + 1] + new_ext)

        n.build(new_name, rule, fn)
        names.append(new_name)

    return names
