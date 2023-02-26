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
from knossos import center, tasks, qt, util


class AutoFetcher(Thread):
    _interval = 60 * 60  # = 1 hour
    _inactive_block = None
    _manual = False

    def __init__(self, interval_type='hourly'):
        super(AutoFetcher, self).__init__()

        self._inactive_block = Condition()
        self.daemon = True

        self.set_interval(interval_type)

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

    def set_interval(self, interval_type):
        if not interval_type in center.FETCH_INTERVALS:
            return

        interval = center.FETCH_INTERVALS[interval_type]

        # if set to manual then we still want to check for
        # updates hourly, but just won't download them
        self._manual = interval == 0
        self._interval = interval if interval > 0 else 60 * 60

    @qt.run_in_qt
    def launch_task(self):
        tasks.run_task(tasks.FetchTask(self._manual))

        if center.settings['update_notify'] and '-dev' not in center.VERSION:
            tasks.run_task(tasks.CheckUpdateTask())
