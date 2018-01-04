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

from __future__ import absolute_import, print_function

import time
import logging

from threading import Thread, Condition
from knossos import center, tasks, qt


class AutoFetcher(Thread):
    _interval = 60 * 60  # = 1 hour
    _inactive_block = None

    def __init__(self):
        super(AutoFetcher, self).__init__()

        self._inactive_block = Condition()
        self.daemon = True

    def trigger(self):
        with self._inactive_block:
            self._inactive_block.notify()

    def run(self):
        while True:
            self.launch_task()
            time.sleep(self._interval)

            if not center.main_win.win.isActiveWindow():
                logging.debug('AutoFetcher paused.')
                with self._inactive_block:
                    self._inactive_block.wait()

                logging.debug('AutoFetcher resumed.')

    @qt.run_in_qt
    def launch_task(self):
        tasks.run_task(tasks.FetchTask())

        if center.settings['update_notify'] and '-dev' not in center.VERSION:
            tasks.run_task(tasks.CheckUpdateTask())
