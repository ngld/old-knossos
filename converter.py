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

from __future__ import absolute_import, print_function
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')
logging.getLogger().addHandler(logging.FileHandler('converter.log'))

import sys
import os
import argparse
import json
import signal
import tempfile
import time
import locale
import shutil
from six import StringIO

from lib import util, progress
from converter.fso_parser import EntryPoint
from lib.qt import QtCore
from converter.repo import RepoConf


class ChecksumTask(progress.Task):

    def work(self, item):
        id_, links, name, archive, tstamp = item

        with tempfile.TemporaryDirectory() as dest:
            path = os.path.join(dest, name)

            for link in links:
                with open(path, 'wb') as stream:
                    res = util.download(link, stream, {'If-Modified-Since': tstamp})

                if res == 304:
                    # Nothing changed.
                    break
                elif res:
                    csum, content = self._inspect_file(id_, archive, dest, path)
                    self.post((id_, csum, content))
                    break

    def _inspect_file(self, id_, archive, dest, path):
        csum = util.gen_hash(path)
        content = {}

        if archive:
            ar_content = os.path.join(dest, 'content')

            if util.extract_archive(path, ar_content):
                for cur_path, dirs, files in os.walk(ar_content):
                    subpath = cur_path[len(ar_content):].replace('\\', '/').lstrip('/')
                    if subpath != '':
                        subpath += '/'

                    for name in files:
                        content[subpath + name] = util.gen_hash(os.path.join(cur_path, name))

                        if name == 'mod.ini':
                            self._inspect_mod_ini(os.path.join(cur_path, name), id_[0])

        return csum, content

    def _inspect_mod_ini(self, path, mid):
        # Let's look for the logo.
        
        base_path = os.path.dirname(path)
        img = []
        with open(path, 'r') as stream:
            for line in stream:
                line = line.strip()
                if line.startswith('image'):
                    line = line.split('=')[1].strip(' \t\n\r;')
                    line = os.path.join(base_path, line)
                    info = os.stat(line)

                    img.append((line, info.st_size))

        # Pick the biggest.
        # TODO: Improve
        img.sort(key=lambda i: i[1])
        img = img[-1][0]

        self.post(((mid, 'logo', 'logo.jpg'), util.convert_img(img, 'jpg'), {}))


def show_progress(prog, text):
    sys.stdout.write('\r %3d%% %s' % (prog * 100, text))
    sys.stdout.flush()


def read_file_list(l):
    if len(l) > 0 and isinstance(l[0], dict):
        res = {}
        for item in l:
            res[item['filename']] = item
        
        return res
    else:
        res = {}
        for urls, files in l:
            for name, info in files.items():
                info = info.copy()
                info['urls'] = [util.pjoin(url, name) for url in urls]
                res[name] = info

        return res


def main(args):
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
        logging.info('Parsing repo...')

        mods = RepoConf(args.repofile)
        mods.parse_includes()

        if len(mods.mods) == 0:
            logging.error('No mods found!')
            return False

        cache = {
            'generated': 0,
            'mods': {}
        }
        start_time = time.time()

        if os.path.isfile(args.outfile):
            with open(args.outfile, 'r') as stream:
                cache = json.load(stream)

            c_mods = {}
            for mod in cache['mods']:
                c_mods[mod['id']] = mod

            cache['mods'] = c_mods

        app = QtCore.QCoreApplication([])
        master = progress.Master()
        task = ChecksumTask()
        
        # Thu, 24 Jul 2014 12:00:16 GMT
        locale.setlocale(locale.LC_TIME, 'C')
        tstamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(cache['generated']))

        items = []
        for mid, mod in mods.mods.items():
            c_mod = cache['mods'].get(mid, {})
            c_pkgs = [pkg['name'] for pkg in c_mod.get('packages', [])]

            for pkg in mod['packages']:
                my_tstamp = 0

                # Only download the files if we have no checksums or they changed.
                if pkg['name'] in c_pkgs:
                    my_tstamp = tstamp

                for name, info in read_file_list(pkg['files']).items():
                    # id_, links, name, archive, tstamp
                    items.append(((mid, pkg['name'], name), info['urls'], name, info.get('is_archive', True), my_tstamp))

        task.add_work(items)
      
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
            signal.signal(signal.SIGINT, lambda a, b: app.quit())
            master.start_workers(5)
            master.add_task(task)
            app.exec_()
            master.stop_workers()
        
        logging.info('Updating checksums...')

        util.QUIET = True
        out = StringIO()
        progress.init_curses(core, out)
        sys.stdout.write(out.getvalue())

        logging.info('Saving data...')

        results = {}
        logos = {}
        for id_, csum, content in task.get_results():
            mid, pkg, name = id_

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

        outpath = os.path.dirname(args.outfile)
        new_cache = {
            'generated': start_time,
            'mods': []
        }

        for mid, mod in mods.mods.items():
            mod = mod.copy()
            c_pkgs = {}
            if mid in cache['mods']:
                for pkg in cache['mods'][mid]['packages']:
                    c_pkgs[pkg['name']] = pkg

            if mid in logos and mod.get('logo', None) is None:
                fd, name = tempfile.mkstemp(dir=outpath, prefix='logo', suffix='.' + logos[mid].split('.')[-1])
                os.close(fd)

                shutil.move(logos[mid], name)
                mod['logo'] = os.path.basename(name)

            for pkg in mod['packages']:
                if pkg['name'] in c_pkgs:
                    files = c_pkgs[pkg['name']]['files']

                    # Prune removed files
                    filenames = set(read_file_list(pkg['files']).keys())
                    for key in set(files.keys()) - filenames:
                        del files[key]
                else:
                    files = {}

                if mid in results and pkg['name'] in results[mid]:
                    files.update(results[mid][pkg['name']])
                elif len(files) == 0:
                    logging.warning('Checksums for "%s" are missing!', mid)

                for name, info in read_file_list(pkg['files']).items():
                    if name not in files:
                        files[name] = {}

                    files[name].update({
                        'filename': name,
                        'is_archive': info.get('is_archive', True),
                        'dest': info.get('dest', '#'),
                        'urls': info['urls']
                    })

                pkg['files'] = files.values()

            new_cache['mods'].append(mod)

        with open(args.outfile, 'w') as stream:
            json.dump(new_cache, stream, separators=(',', ':'))

        # Cleanup
        for path in logos.values():
            if os.path.isfile(path):
                os.unlink(path)

        logging.info('Done')
    elif args.action == 'list':
        mods = RepoConf(args.repofile)

        print('\n'.join(sorted(mods.mods.keys())))
    else:
        logging.error('You have to specify a valid action!')
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])
