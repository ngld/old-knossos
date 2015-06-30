## Copyright 2014 Knossos authors, see NOTICE file
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
import argparse
import logging
import json
import signal
import tempfile
import time
import locale
import shutil
from six import StringIO

from knossos import util, progress
# from .fso_parser import EntryPoint
from knossos.qt import QtCore
from .repo import RepoConf
from .tasks import ChecksumTask


app = None
pmaster = None


def show_progress(prog, text):
    sys.stdout.write('\r %3d%% %s' % (prog * 100, text))
    sys.stdout.flush()


def init_app():
    global app, pmaster

    if app is None:
        app = QtCore.QCoreApplication([])
        pmaster = progress.Master()
    else:
        app.reset()

    return app


def run_task(task, prg_wrap=None, use_curses=False):
    def update_progress(pi):
        total, items, title = pi
        text = []
        for item in items.values():
            if item[0] > 0:
                text.append('%3d%% %s' % (item[0] * 100, item[1]))
        
        progress.update(total, '\n'.join(text))
    
    def finish():
        app.quit()
    
    if prg_wrap is not None or use_curses:
        task.progress.connect(update_progress)
    
    task.done.connect(finish)
    
    def core():
        if prg_wrap is None:
            signal.signal(signal.SIGINT, lambda a, b: app.quit())

        pmaster.start_workers(3)
        pmaster.add_task(task)
        app.exec_()
        pmaster.stop_workers()

    util.QUIET = True
    util.QUIET_EXC = True

    if prg_wrap is not None:
        prg_wrap(core)
    else:
        out = StringIO()
        if use_curses:
            try:
                progress.init_curses(core, out)
            except:
                core()

            sys.stdout.write(out.getvalue())
        else:
            core()


def generate_checksums(repo, output, prg_wrap=None, dl_path=None, dl_mirror=None, curses=False, force_cache=False, list_files=False):
    logging.info('Parsing repo...')

    mods = RepoConf(repo)
    mods.parse_includes()

    if len(mods.mods) == 0:
        logging.error('No mods found!')
        return False

    if not mods.validate():
        logging.error('Failed to parse the repo!')
        return False

    cache = {
        'generated': 0,
        'mods': {}
    }
    start_time = time.time()
    failed = False
    results = {}

    if os.path.isfile(output):
        with open(output, 'r') as stream:
            stream.seek(0, os.SEEK_END)

            # Don't try to parse the file if it's empty.
            if stream.tell() != 0:
                stream.seek(0)
                cache = json.load(stream)

        c_mods = {}
        for mod in cache['mods']:
            if mod['id'] not in c_mods:
                c_mods[mod['id']] = {}

            c_mods[mod['id']][mod['version']] = mod

        cache['mods'] = c_mods

    # Thu, 24 Jul 2014 12:00:16 GMT
    locale.setlocale(locale.LC_TIME, 'C')
    tstamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(cache['generated']))

    items = []
    for mid, mvs in mods.mods.items():
        for ver, mod in mvs.items():
            c_mod = cache['mods'].get(mid, {}).get(str(ver), {})
            c_pkgs = [pkg['name'] for pkg in c_mod.get('packages', [])]

            for pkg in mod.packages:
                my_tstamp = 0

                if force_cache and pkg.name in c_pkgs:
                    if mid not in results:
                        results[mid] = {}

                    if ver not in results[mid]:
                        results[mid][ver] = {}

                    if pkg.name not in results[mid][ver]:
                        results[mid][ver][pkg.name] = {}

                    for name, file_ in pkg.files.items():
                        results[mid][ver][pkg.name][name] = {
                            'md5sum': 'CACHE',
                            'contents': [],
                            'size': 0
                        }

                    continue

                # Only download the files if we have no checksums or they changed.
                if pkg.name in c_pkgs:
                    my_tstamp = tstamp

                for name, file_ in pkg.files.items():
                    # id_, links, name, archive, tstamp
                    items.append(((mid, mod.version, pkg.name, name), file_.urls, name, file_.is_archive, my_tstamp))
    
    if len(items) < 1:
        if not force_cache:
            logging.error('No files found!')
            failed = True

        file_info = []
    else:
        logging.info('Generating checksums...')

        init_app()
        task = ChecksumTask(items, dl_path, dl_mirror)
        run_task(task, prg_wrap, curses)
        file_info = task.get_results()

    logging.info('Saving data...')

    logos = {}
    for id_, csum, content, size in file_info:
        mid, ver, pkg, name = id_

        if csum == 'FAILED':
            failed = True
            continue

        if name == 'logo.jpg':
            if mid not in logos:
                logos[mid] = {}

            logos[mid][ver] = csum
        else:
            if mid not in results:
                results[mid] = {}

            if ver not in results[mid]:
                results[mid][ver] = {}

            if pkg not in results[mid][ver]:
                results[mid][ver][pkg] = {}

            results[mid][ver][pkg][name] = {
                'md5sum': csum,
                'contents': content,
                'size': size
            }

    outpath = os.path.dirname(output)
    new_cache = {
        'generated': start_time,
        'mods': []
    }

    # Well, this looks horrible...
    # This loop copies the Mod objects from mods, adds the data from results and places the objects in new_cache['mods'].
    # It also merges in data from cache['mods'] if necessary (whenever the md5sum of a file/archive is set to CACHE).
    for mid, mvs in mods.mods.items():
        for ver, mod in mvs.items():
            mod = mod.copy()
            c_pkgs = {}
            sver = str(ver)

            # Retrieve our packages from cache
            if mid in cache['mods'] and sver in cache['mods'][mid]:
                for pkg in cache['mods'][mid][sver]['packages']:
                    c_pkgs[pkg['name']] = pkg.copy()

            if mid in logos and ver in logos[mid] and mod.logo is None:
                fd, name = tempfile.mkstemp(dir=outpath, prefix='logo', suffix='.' + logos[mid][ver].split('.')[-1])
                os.close(fd)

                shutil.move(logos[mid][ver], name)
                mod.logo = os.path.basename(name)

            for pkg in mod.packages:
                c_files = {}
                files = {}

                # Retrieve our files from cache
                if pkg.name in c_pkgs:
                    for item in c_pkgs[pkg.name]['files']:
                        c_files[item['filename']] = item

                    for item in c_pkgs[pkg.name]['filelist']:
                        if item['orig_name'] is None:
                            continue

                        ar = c_files[item['archive']]
                        if 'contents' not in ar:
                            ar['contents'] = {}

                        ar['contents'][item['orig_name']] = item['md5sum']

                # Look for files which should keep their old checksum (from cache).
                if mid in results and ver in results[mid] and pkg.name in results[mid][ver]:
                    files = results[mid][ver][pkg.name]
                    for name, info in files.items():
                        if info['md5sum'] == 'CACHE':
                            if name not in c_files:
                                logging.error('Tried to retrieve a checksum from the cache but it was\'t there! (This is a bug!)')
                                failed = True
                            else:
                                info['md5sum'] = c_files[name]['md5sum']
                                info['contents'] = c_files[name]['contents']
                                info['size'] = c_files[name]['filesize']
                else:
                    logging.error('Checksums for "%s" are missing!', mid)
                    failed = True

                # Copy the information from rests
                for name, info in pkg.files.items():
                    if name not in files:
                        logging.error('Missing information for file "%s" of package "%s".', name, pkg.name)
                    else:
                        info.md5sum = files[name]['md5sum']
                        info.contents = files[name]['contents']
                        info.filesize = files[name]['size']

            mod.build_file_list()

            # Check files
            done = False
            for pkg in mod.packages:
                for item in pkg.filelist:
                    if item['filename'].endswith('mod.ini'):
                        if item['filename'] == 'mod.ini':
                            # All is well...
                            done = True
                            break
                        else:
                            prefix = item['filename'][:-7].strip('/')

                            logging.warn('Found mod.ini in folder %s. I assume you forgot the move action; I\'ll just add it myself.', prefix)
                            mod.actions.append({
                                'type': 'move',
                                'paths': [prefix + '/*'],
                                'dest': '',
                                'glob': True
                            })
                            mod.build_file_list()

                            done = True
                            break

                if done:
                    break

            if list_files:
                file_list = [
                    'Please make sure the following is correct:',
                    'If a user has FS installed in C:\\Freespace2, your mod will install the following files:',
                    ''
                ]
                prefix = 'C:\\Freespace2\\' + mod.folder
                for pkg in mod.packages:
                    for item in pkg.filelist:
                        file_list.append(prefix + '\\' + item['filename'].replace('/', '\\'))

                logging.info('\n'.join(file_list))

            new_cache['mods'].append(mod.get())

    with open(output, 'w') as stream:
        json.dump(new_cache, stream, separators=(',', ':'))

    # Cleanup
    for path in logos.values():
        if os.path.isfile(path):
            os.unlink(path)

    if failed:
        logging.error('Failed!')
        return False
    else:
        logging.info('Done')
        return True


def main(args, prg_wrap=None):
    # Default to replace errors when de/encoding.
    import codecs
    
    codecs.register_error('strict', codecs.replace_errors)
    codecs.register_error('really_strict', codecs.strict_errors)
    
    progress.reset()
    progress.set_callback(show_progress)
    
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='action')
    
    checksums_parser = subs.add_parser('checksums', help='Generate checksums for all referenced files.')
    checksums_parser.add_argument('--save-files', dest='dl_path', help='Save the downloaded files.', default=None)
    checksums_parser.add_argument('--no-curses', dest='no_curses', action='store_true', default=False, help="Don't use the Curses UI.")
    checksums_parser.add_argument('--force-cache', dest='force_cache', action='store_true', default=False, help="Skip files which have been downloaded before.")
    checksums_parser.add_argument('--list-files', dest='list_files', action='store_true', default=False, help="List the mod's files once the conversion is finished.")
    checksums_parser.add_argument('repofile', help='The configuration used to locate the files.')
    checksums_parser.add_argument('outfile', help='The path to the generated configuration.')

    list_parser = subs.add_parser('list', help='list mods')
    list_parser.add_argument('repofile', help='The repository configuration.')

    args = parser.parse_args(args)
    
    if args.action == 'checksums':
        generate_checksums(args.repofile, args.outfile, dl_path=args.dl_path, curses=not args.no_curses, force_cache=args.force_cache, list_files=args.list_files)
    elif args.action == 'list':
        mods = RepoConf(args.repofile)

        print('\n'.join(sorted(mods.mods.keys())))
    else:
        logging.error('You have to specify a valid action!')
        sys.exit(1)
