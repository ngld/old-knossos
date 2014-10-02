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

from lib import util, progress
from .fso_parser import EntryPoint
from lib.qt import QtCore
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

    return app


def run_task(task, prg_wrap=None):
    def update_progress():
        total, items = task.get_progress()
        text = []
        for item in items.values():
            text.append('%3d%% %s' % (item[0] * 100, item[1]))
        
        progress.update(total, '\n'.join(text))
    
    def finish():
        app.quit()
    
    task.progress.connect(update_progress)
    task.done.connect(finish)
    
    def core():
        if prg_wrap is None:
            signal.signal(signal.SIGINT, lambda a, b: app.quit())

        pmaster.start_workers(5)
        pmaster.add_task(task)
        app.exec_()
        pmaster.stop_workers()

    util.QUIET = True
    util.QUIET_EXC = True

    if prg_wrap is not None:
        prg_wrap(core)
    else:
        out = StringIO()
        progress.init_curses(core, out)
        sys.stdout.write(out.getvalue())


def generate_checksums(repo, output, prg_wrap=None):
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

    if os.path.isfile(output):
        with open(output, 'r') as stream:
            stream.seek(0, os.SEEK_END)

            # Don't try to parse the file if it's empty.
            if stream.tell() != 0:
                stream.seek(0)
                cache = json.load(stream)

        c_mods = {}
        for mod in cache['mods']:
            c_mods[mod['id']] = mod

        cache['mods'] = c_mods

    # Thu, 24 Jul 2014 12:00:16 GMT
    locale.setlocale(locale.LC_TIME, 'C')
    tstamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(cache['generated']))

    items = []
    for mid, mod in mods.mods.items():
        c_mod = cache['mods'].get(mid, {})
        c_pkgs = [pkg['name'] for pkg in c_mod.get('packages', [])]

        for pkg in mod.packages:
            my_tstamp = 0

            # Only download the files if we have no checksums or they changed.
            if pkg.name in c_pkgs:
                my_tstamp = tstamp

            for name, file_ in pkg.files.items():
                # id_, links, name, archive, tstamp
                items.append(((mid, pkg.name, name), file_.urls, name, file_.is_archive, my_tstamp))
    
    logging.info('Updating checksums...')

    init_app()
    task = ChecksumTask()
    task.add_work(items)
    run_task(task, prg_wrap)

    logging.info('Saving data...')

    results = {}
    logos = {}
    for id_, csum, content in task.get_results():
        mid, pkg, name = id_

        if csum == 'FAILED':
            failed = True
            continue

        if name == 'logo.jpg':
            logos[mid] = csum
        else:
            if mid not in results:
                results[mid] = {}

            if pkg not in results[mid]:
                results[mid][pkg] = {}

            results[mid][pkg][name] = {
                'md5sum': csum,
                'contents': content
            }

    outpath = os.path.dirname(output)
    new_cache = {
        'generated': start_time,
        'mods': []
    }

    for mid, mod in mods.mods.items():
        mod = mod.copy()
        c_pkgs = {}
        if mid in cache['mods']:
            for pkg in cache['mods'][mid]['packages']:
                c_pkgs[pkg['name']] = pkg.copy()

        if mid in logos and mod.logo is None:
            fd, name = tempfile.mkstemp(dir=outpath, prefix='logo', suffix='.' + logos[mid].split('.')[-1])
            os.close(fd)

            shutil.move(logos[mid], name)
            mod.logo = os.path.basename(name)

        for pkg in mod.packages:
            c_files = {}
            files = {}

            if pkg.name in c_pkgs:
                for item in c_pkgs[pkg.name]['files']:
                    c_files[item['filename']] = item

            if mid in results and pkg.name in results[mid]:
                files = results[mid][pkg.name]
                for name, info in files.items():
                    if info['md5sum'] == 'CACHE':
                        if name not in c_files:
                            logging.error('Tried to retrieve a checksum from the cache but it was\'t there! (This is a bug!)')
                            failed = True
                        else:
                            info['md5sum'] = c_files[name]['md5sum']
                            info['contents'] = c_files[name]['contents']
            else:
                logging.error('Checksums for "%s" are missing!', mid)
                failed = True

            for name, info in pkg.files.items():
                if name not in files:
                    logging.error('Missing information for file "%s" of package "%s".', name, pkg.name)
                else:
                    info.md5sum = files[name]['md5sum']
                    info.contents = files[name]['contents']

        mod.build_file_list()
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
    progress.reset()
    progress.set_callback(show_progress)
    
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='action')
    
    import_parser = subs.add_parser('import', help='import installer text files')
    import_parser.add_argument('repofile', help='The imported files will be stored inside this file.')

    checksums_parser = subs.add_parser('checksums', help='Generate checksums for all referenced files.')
    checksums_parser.add_argument('-p', dest='pretty', help='pretty print the output', action='store_true')
    checksums_parser.add_argument('repofile', help='The configuration used to locate the files.')
    checksums_parser.add_argument('outfile', help='The path to the generated configuration.')

    list_parser = subs.add_parser('list', help='list mods')
    list_parser.add_argument('repofile', help='The repository configuration.')

    args = parser.parse_args(args)
    
    if args.action == 'import':
        if not os.path.isfile(args.repofile):
            logging.warning('The file "%s" wasn\'t found. I will be creating it from scratch.', args.repofile)
            mods = RepoConf()
        else:
            mods = RepoConf(args.repofile)

        logging.info('Fetching installer text files...')
        mod_tree = EntryPoint.get_mods()

        logging.info('Converting...')
        mods.import_tree(mod_tree)

        mods.write(args.repofile, True)
        logging.info('Done')
    elif args.action == 'checksums':
        generate_checksums(args.repofile, args.outfile)
    elif args.action == 'list':
        mods = RepoConf(args.repofile)

        print('\n'.join(sorted(mods.mods.keys())))
    else:
        logging.error('You have to specify a valid action!')
        sys.exit(1)
