#!/usr/bin/env python
"""
Downloads and extracts an archive based on a provided manifest.
"""

from __future__ import print_function
import locale
import os
import signal
import sys
import threading
import time
import json
import tempfile
import tarfile
import hashlib

from etaprogress.progress import ProgressBarWget
import requests


def error(message, code=1):
    """Prints an error message to stderr and exits with a status of 1 by default."""
    if message:
        print('ERROR: {0}'.format(message), file=sys.stderr)
    else:
        print(file=sys.stderr)
    sys.exit(code)


class DownloadThread(threading.Thread):
    """Downloads the file, but doesn't save it (just the file size)."""

    def __init__(self, response, checksum):
        super(DownloadThread, self).__init__()
        self.response = response
        self.checksum = checksum

        self._bytes_downloaded = 0
        self._failed = False
        self.daemon = True

    def run(self):
        with tempfile.TemporaryFile() as archive:
            hashgen = hashlib.new(self.checksum[0])

            for chunk in self.response.iter_content(1024):
                self._bytes_downloaded += len(chunk)

                archive.write(chunk)
                hashgen.update(chunk)

            if hashgen.hexdigest() != self.checksum[1]:
                self._failed = True
                return

            archive.seek(0)
            tar = tarfile.open(mode='r:gz', fileobj=archive)
            tar.extractall()

    @property
    def bytes_downloaded(self):
        """Read-only interface to _bytes_downloaded."""
        return self._bytes_downloaded

    @property
    def failed(self):
        return self._failed


def main():
    """From: http://stackoverflow.com/questions/20801034/how-to-measure-download-speed-and-progress-using-requests"""
    # Prepare.
    if os.name == 'nt':
        locale.setlocale(locale.LC_ALL, 'english-us')
    else:
        locale.resetlocale()

    if len(sys.argv) < 2:
        error('Path to manifest is missing!')

    manifest = sys.argv[1]
    os.chdir(os.path.dirname(manifest))

    with open(os.path.basename(manifest), 'r') as hdl:
        meta = json.load(hdl)

    chk_file = os.path.basename(manifest) + '.chk'
    last_chk = None
    if os.path.isfile(chk_file):
        with open(chk_file, 'r') as stream:
            last_chk = stream.read().strip()

        if last_chk == '#'.join(meta['checksum']):
            return

    print('%s has changed or has not been downloaded, yet. Downloading...' % manifest)

    response = requests.get(meta['url'], stream=True)
    content_length = None if meta.get('ignore_length', False) else int(response.headers.get('Content-Length', 0))
    progress_bar = ProgressBarWget(content_length, eta_every=4)
    thread = DownloadThread(response, meta['checksum'])
    print_every_seconds = 0.25

    # Download.
    thread.start()
    while True:
        progress_bar.numerator = thread.bytes_downloaded
        print(progress_bar, end='\r')
        sys.stdout.flush()

        # For undefined downloads (no content-length), check if thread has stopped. Loop only checks defined downloads.
        if not thread.isAlive():
            progress_bar.force_done = True
            break
        if progress_bar.done:
            break

        time.sleep(print_every_seconds)

    print(progress_bar)  # Always print one last time.

    if thread.failed:
        error('The download failed because the download was incomplete or corrupted!')

    thread.join()

    with open(chk_file, 'w') as stream:
        stream.write('#'.join(meta['checksum']))


if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda *_: error('', 0))  # Properly handle Control+C
    main()
