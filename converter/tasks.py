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
import tempfile
import logging
from threading import Lock

from knossos import progress, util


class ChecksumTask(progress.Task):
    dl_path = None
    dl_mirror = None
    _mf_lock = None

    def __init__(self, work, dl_path=None, dl_mirror=None):
        super(ChecksumTask, self).__init__(work)

        self.dl_path = dl_path
        self.dl_mirror = dl_mirror
        self._mf_lock = Lock()

    def work(self, item):
        id_, links, name, archive, tstamp = item
        
        with tempfile.TemporaryDirectory() as dest:
            if self.dl_path is None:
                base_path = dest
            else:
                base_path = self.dl_path

            f_name = os.path.basename(name)
            path = os.path.join(base_path, f_name)
            idx = 1
            while os.path.exists(path):
                path = os.path.join(base_path, str(idx) + '_' + f_name)
                idx += 1

            res = self._download(links, path, tstamp)

            if res == 304:
                # Nothing changed.
                self.post((id_, 'CACHE', None))
            elif res:
                logging.info('Inspecting "%s"...', name)
                progress.update(1, 'Inspecting "%s"...' % name)
                
                csum, content = self._inspect_file(id_, archive, dest, path)

                if csum != 'FAILED':
                    if self.dl_mirror is not None:
                        links.append(util.pjoin(self.dl_mirror, os.path.basename(path)))

                    self.post((id_, csum, content))
                else:
                    self.post((id_, 'FAILED', None))
            else:
                # None of the links worked!
                self.post((id_, 'FAILED', None))

    def _download(self, links, path, tstamp):
        from . import download

        all_links = links[:]

        # Remove all indirect links.
        for i, link in reversed(list(enumerate(links))):
            if not download.is_direct(link):
                del links[i]

        for link in all_links:
            res = download.download(link, path)

            if res is None:
                with open(path, 'wb') as stream:
                    res = util.download(link, stream, headers={'If-Modified': tstamp})

            if res == 304 or res:
                return res

        return False

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
            else:
                logging.error('Failed to extract "%s"!', os.path.basename(path))
                return 'FAILED', None

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
