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
import shutil
from threading import Lock

from knossos import progress, util


class ChecksumTask(progress.Task):
    dl_path = None
    dl_mirror = None
    dl_slug = None
    rem_prefixes = None
    _mf_lock = None

    def __init__(self, work, dl_path=None, dl_mirror=None, dl_slug=None, remove_prefixes=[]):
        super(ChecksumTask, self).__init__(work)

        self.dl_path = dl_path
        self.dl_mirror = dl_mirror
        self.dl_slug = dl_slug
        self.rem_prefixes = remove_prefixes
        self._mf_lock = Lock()

    def work(self, item):
        id_, links, name, archive, tstamp = item
        
        with tempfile.TemporaryDirectory() as dest:
            if self.dl_path is None:
                base_path = dest
            else:
                base_path = os.path.join(self.dl_path, self.dl_slug)

            f_name = os.path.basename(name)
            path = os.path.join(base_path, f_name)
            idx = 1
            while os.path.exists(path):
                path = os.path.join(base_path, str(idx) + '_' + f_name)
                idx += 1

            res = self._download(links, path, tstamp)

            for i, link in reversed(list(enumerate(links))):
                for pref in self.rem_prefixes:
                    if link.startswith(pref):
                        del links[i]

            if res == 304:
                # Nothing changed.
                self.post((id_, 'CACHE', None, 0))
            elif res:
                logging.info('Inspecting "%s"...', name)
                progress.update(0.999, 'Inspecting "%s"...' % name)
                
                csum, content = self._inspect_file(id_, archive, dest, path)

                if csum != 'FAILED':
                    if self.dl_mirror is not None:
                        links.append(util.pjoin(self.dl_mirror, self.dl_slug, os.path.basename(path)))

                    self.post((id_, csum, content, os.path.getsize(path)))
                else:
                    os.unlink(path)
                    self.post((id_, 'FAILED', None, 0))
            else:
                # None of the links worked!
                self.post((id_, 'FAILED', None, 0))

    def _download(self, links, path, tstamp):
        from . import download

        all_links = links[:]
        retries = 5

        # Remove all indirect links.
        for i, link in reversed(list(enumerate(links))):
            if not download.is_direct(link):
                del links[i]

        while retries > 0:
            retries -= 1
            
            for link in all_links:
                if self.dl_mirror is not None and link.startswith(self.dl_mirror):
                    link_path = os.path.join(self.dl_path, link[len(self.dl_mirror):].lstrip('/'))
                    if os.path.isfile(link_path):
                        shutil.copyfile(link_path, path)
                        return True

                with open(path, 'wb') as stream:
                    res = util.download(link, stream, headers={'If-Modified': str(tstamp)})

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
                        fpath = os.path.join(cur_path, name)

                        # Don't generate checksums for symlinks.
                        if not os.path.islink(fpath):
                            content[subpath + name] = util.gen_hash(fpath)
            else:
                logging.error('Failed to extract "%s"!', os.path.basename(path))
                return 'FAILED', None

        return csum, content
