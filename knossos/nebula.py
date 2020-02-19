import os.path
import logging
import hashlib
import math
import time
import requests

from threading import Thread, Lock
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from . import center, progress, util


class InvalidLoginException(Exception):
    pass


class RequestFailedException(Exception):
    pass


class AccessDeniedException(RequestFailedException):
    pass


class BufferingMultipartEncoder(MultipartEncoder):
    chunk_size = 4 * 1024  # 4 KiB

    def _calculate_load_amount(self, read_size):
        needed = read_size - self._buffer.len

        if needed > 0:
            return max(self.chunk_size, needed)
        else:
            return 0


class FileWrapper:

    def __init__(self, hdl, size):
        self._hdl = hdl
        self._hasher = hashlib.new('sha256')

        pos = hdl.tell()
        hdl.seek(0, os.SEEK_END)

        # Correct the size if the remaining amount of data is less
        self._end = min(pos + size, hdl.tell())
        self.len = self._end - pos

        hdl.seek(pos)

    def read(self, size=None):
        if not size:
            size = self.len
        elif self.len <= 0:
            return b''
        elif size > self.len:
            size = self.len

        chunk = self._hdl.read(size)
        self._hasher.update(chunk)
        self.len -= size
        return chunk

    def get_hash(self):
        return self._hasher.hexdigest()


class UploadWorker(Thread):

    def __init__(self, manager):
        super(UploadWorker, self).__init__()

        self._manager = manager
        self.daemon = True
        self.start()

    def run(self):
        hdl = self._manager.get_hdl()
        neb = self._manager.neb
        uid = self._manager.upload_id

        try:
            while True:
                idx, offset = self._manager.get_part()

                if idx is None:
                    # We're done
                    return

                hdl.seek(offset)

                try:
                    # result = neb._call('multiupload/check', data={
                    #     'id': uid,
                    #     'part': idx
                    # })
                    # data = result.json()

                    # if data.get('result'):
                    #     # Already uploaded
                    #     self._manager.done(idx)
                    #     continue

                    wrapper = FileWrapper(hdl, self._manager.part_size)
                    enc = BufferingMultipartEncoder({
                        'id': uid,
                        'part': str(idx),
                        'file': ('upload', wrapper, 'application/octet-stream')
                    })

                    # enc_len = enc.len

                    # def cb(monitor):
                    #     progress.update(monitor.bytes_read / enc_len, 'Uploading %s...' % name)

                    # monitor = MultipartEncoderMonitor(enc, cb)

                    neb._call('multiupload/part', data=enc, timeout=10 * 60, retry=0, headers={  # timeout = 10 minutes (for ~10 MiB)
                        'Content-Type': enc.content_type
                    })

                    result = neb._call('multiupload/verify_part', data={
                        'id': uid,
                        'part': str(idx),
                        'checksum': wrapper.get_hash()
                    })
                    data = result.json()

                    if data.get('result'):
                        self._manager.done(idx)
                    else:
                        self._manager.failed(idx)
                except Exception:
                    logging.exception('Failed to upload part %d for upload %s' % (idx, self._manager.name))
                    self._manager.failed(idx)

        except Exception:
            logging.exception('Worker exception during multi-upload for %s' % self._manager.name)
        finally:
            hdl.close()
            self._manager._remove_worker(self)


class MultipartUploader:
    upload_id = None
    part_size = 10 * 1024 * 1024  # 10 MiB
    _retries = 0
    _aborted = False

    def __init__(self, nebula, name, path, content_checksum, vp_checksum):
        self.neb = nebula
        self.name = name
        self._path = path
        self._content_checksum = content_checksum
        self._vp_checksum = vp_checksum
        self._workers = []
        self._parts_left = []
        self._parts_done = set()
        self._parts_lock = Lock()
        self._progress = None

    def run(self, worker_count=3):
        progress.update(0, 'Hashing...')
        _, checksum = util.gen_hash(self._path)

        size = os.stat(self._path).st_size
        with self._parts_lock:
            self._parts_left = list(range(math.ceil(size / self.part_size)))
        self.upload_id = checksum

        progress.update(0.1, 'Registering...')
        try:
            result = self.neb._call('multiupload/start', data={
                'id': checksum,
                'size': size,
                'parts': len(self._parts_left)
            })
            data = result.json()
            if data.get('done'):
                progress.update(1, 'Already uploaded')
                with self._parts_lock:
                    self._parts_done = set(self._parts_left)
                    self._parts_left = []
                return True

            if not data.get('result'):
                raise Exception('Multiupload failed for unkown reasons')

            if data.get('finished_parts'):
                with self._parts_lock:
                    self._parts_done = set(data['finished_parts'])
                    for p in self._parts_done:
                        self._parts_left.remove(p)
        except Exception:
            logging.exception('Multiupload %s failed to start.' % self.name)
            return False

        progress.update(0.1, 'Starting workers...')
        for i in range(worker_count):
            self._workers.append(UploadWorker(self))

        with self._parts_lock:
            self._update_status()

        # Wait for them to finish
        while self._workers:
            time.sleep(0.5)

            if self._progress:
                # Forward progress updates from the worker threads
                progress.update(*self._progress)
                self._progress = None

        if self._aborted:
            return False

        progress.update(0.95, 'Verifying...')
        try:
            result = self.neb._call('multiupload/finish', timeout=10 * 60 * 60, data={
                'id': checksum,
                'checksum': checksum,
                'content_checksum': self._content_checksum,
                'vp_checksum': self._vp_checksum
            })
            data = result.json()

            if not data.get('result'):
                raise Exception('Multiupload failed for unkown reasons')
        except Exception:
            logging.exception('Multiupload %s failed to start.' % self.name)
            return False

        progress.update(1, 'Done')
        return True

    def _remove_worker(self, w):
        if w in self._workers:
            self._workers.remove(w)

    def get_hdl(self):
        return open(self._path, 'rb')

    def get_part(self):
        with self._parts_lock:
            if self._parts_left and not self._aborted:
                p = self._parts_left.pop(0)
                return (p, self.part_size * p)
            else:
                return (None, None)

    def done(self, idx):
        logging.debug('%s: Part %d done.' % (self.name, idx))

        with self._parts_lock:
            self._parts_done.add(idx)
            self._update_status()

    def failed(self, idx):
        logging.debug('%s: Part %d failed.' % (self.name, idx))
        self._retries += 1

        with self._parts_lock:
            self._parts_left.append(idx)
            self._update_status()

    def _update_status(self):
        done = len(self._parts_done)
        left = len(self._parts_left)

        if done + left == 0:
            logging.warning('No parts for updating status!')
            return

        total = float(done + left)

        self._progress = (
            (done / total * 0.85) + 0.1,
            'Uploading... %3d / %3d, %d retried' % (done, total, self._retries)
        )

    def abort(self):
        self._aborted = True

        with self._parts_lock:
            self._parts_left = []


class NebulaClient(object):
    _token = None
    _sess = None

    def __init__(self):
        self._sess = util.HTTP_SESSION
        self._uploads = []

    def _call(self, path, method='POST', skip_login=False, check_code=True, retry=3, **kwargs):
        url = center.API + path

        if not skip_login and not self._token:
            if not self.login():
                raise InvalidLoginException()

        if self._token:
            headers = kwargs.setdefault('headers', {})
            headers['X-KN-TOKEN'] = self._token

        kwargs.setdefault('timeout', 60)

        for i in range(retry + 1):
            try:
                try:
                    result = self._sess.request(method, url, **kwargs)
                except requests.RequestException:
                    logging.exception('Failed to send %s request to %s!' % (method, path))
                    raise RequestFailedException('connection')

                if check_code and result.status_code != 200:
                    reason = 'unknown'
                    if result.status_code == 404:
                        reason = 'not found'

                    raise RequestFailedException(reason)

                break
            except Exception:
                if i == retry:
                    raise
                else:
                    time.sleep(0.3)

        return result

    def login(self, user=None, password=None):
        # TODO: Switch to token-based authentication instead of password-based.

        if not user:
            user = center.settings['neb_user']
            password = center.settings['neb_password']

        try:
            result = self._call('login', skip_login=True, data={
                'user': user,
                'password': password
            })
        except Exception:
            return False

        data = result.json()
        if data['result']:
            self._token = data['token']
            return True
        else:
            return False

    def register(self, user, password, email):
        self._call('register', skip_login=True, retry=0, data={
            'name': user,
            'password': password,
            'email': email
        })

        return True

    def reset_password(self, user):
        self._call('reset_password', skip_login=True, retry=0, data={'user': user})
        return True

    def get_editable_mods(self):
        result = self._call('mod/editable', 'GET')
        return result.json()['mods']

    def is_editable(self, mid):
        result = self._call('mod/is_editable', data={'mid': mid})
        return result.json()

    def _upload_mod_logos(self, mod):
        chks = [None, None]

        for i, prop in enumerate(('logo', 'tile')):
            im = getattr(mod, prop)
            if im and os.path.isfile(im):
                chks[i] = util.gen_hash(im)[1]
                self.upload_file(prop, im)

        return chks

    def check_mod_id(self, mid, title=None):
        result = self._call('mod/check_id', data={
            'id': mid,
            'title': title
        })

        return result.json()['result']

    def create_mod(self, mod):
        logo_chk, tile_chk = self._upload_mod_logos(mod)

        self._call('mod/create', retry=0, json={
            'id': mod.mid,
            'title': mod.title,
            'type': mod.mtype,
            'parent': mod.parent,
            'logo': logo_chk,
            'tile': tile_chk,
            'first_release': mod.first_release.strftime('%Y-%m-%d') if mod.first_release else None,
            'members': []
        })
        return True

    def update_mod(self, mod):
        # TODO: Check if these actually changed
        logo_chk, tile_chk = self._upload_mod_logos(mod)

        self._call('mod/update', json={
            'id': mod.mid,
            'title': mod.title,
            'logo': logo_chk,
            'tile': tile_chk,
            'first_release': mod.first_release.strftime('%Y-%m-%d') if mod.first_release else None,
            'members': [center.settings['neb_user']]
        })
        return True

    def preflight_release(self, mod, private=False):
        meta = mod.get()
        meta['screenshots'] = []
        meta['attachments'] = []
        meta['banner'] = ''
        meta['private'] = private

        result = self._call('mod/release/preflight', json=meta)
        data = result.json()
        if not data:
            raise RequestFailedException()

        if data['result']:
            return True

        if data.get('reason') == 'unauthorized':
            raise AccessDeniedException()

        raise RequestFailedException(data.get('reason'))

    def _prepare_release(self, mod, private):
        meta = mod.get()

        for prop in ('screenshots', 'attachments'):
            sums = []
            for fn in meta[prop]:
                path = os.path.join(mod.folder, fn)

                if os.path.isfile(path):
                    chk = util.gen_hash(path)[1]

                    self.upload_file(fn, path)
                    sums.append(chk)

            meta[prop] = sums

        if meta['banner']:
            image = os.path.join(mod.folder, meta['banner'])

            if os.path.isfile(image):
                meta['banner'] = util.gen_hash(image)[1]
                self.upload_file('banner', image)

        meta['private'] = private
        return meta

    def create_release(self, mod, private=False):
        meta = self._prepare_release(mod, private)
        result = self._call('mod/release', json=meta)
        data = result.json()
        if not data:
            raise RequestFailedException('unknown')

        if data['result']:
            return True

        if data.get('reason') == 'unauthorized':
            raise AccessDeniedException(data['reason'])

        raise RequestFailedException(data.get('reason'))

    def update_release(self, mod, private=False):
        meta = self._prepare_release(mod, private)
        result = self._call('mod/release/update', json=meta)
        data = result.json()
        if not data:
            raise RequestFailedException('unknown')

        if data['result']:
            return True

        if data.get('reason') == 'unauthorized':
            raise AccessDeniedException(data['reason'])

        raise RequestFailedException(data.get('reason'))

    def report_release(self, mod, message):
        result = self._call('mod/release/report', data={
            'mid': mod.mid,
            'version': str(mod.version),
            'message': message
        })
        data = result.json()
        if not data or not data.get('result'):
            raise RequestFailedException('unknown')

        return True

    def delete_release(self, mod):
        result = self._call('mod/release/delete', retry=1, data={
            'mid': mod.mid,
            'version': str(mod.version)
        })
        data = result.json()
        if not data or not data.get('result'):
            if data.get('reason') == 'unauthorized':
                raise AccessDeniedException(data['reason'])
            else:
                raise RequestFailedException('unknown')

        return True

    def upload_file(self, name, path, fn=None, content_checksum=None, vp_checksum=None):
        _, checksum = util.gen_hash(path)

        result = self._call('upload/check', data={'checksum': checksum})
        data = result.json()
        if data.get('result'):
            # Already uploaded
            return True

        if vp_checksum:
            assert vp_checksum[0] == 'sha256'
            vp_checksum = vp_checksum[1]

        hdl = open(path, 'rb')
        enc = MultipartEncoder({
            'checksum': checksum,
            'content_checksum': content_checksum,
            'vp_checksum': vp_checksum,
            'file': ('upload', hdl, 'application/octet-stream')
        })

        enc_len = enc.len

        def cb(monitor):
            progress.update(monitor.bytes_read / enc_len, 'Uploading %s...' % name)

        monitor = MultipartEncoderMonitor(enc, cb)
        # TODO: Implement incremental uploads to get rid of this insanity
        self._call('upload/file', data=monitor, timeout=3 * 60 * 60, headers={  # timeout = 3 hours
            'Content-Type': monitor.content_type
        })

        return True

    def multiupload_file(self, name, path, fn=None, content_checksum=None, vp_checksum=None):
        progress.start_task(0, 1, '%s: %%s' % name)

        uploader = None
        try:
            uploader = MultipartUploader(self, name, path, content_checksum, vp_checksum)
            self._uploads.append(uploader)

            result = uploader.run()
        except Exception:
            logging.exception('MultipartUploader bug!')
            result = False
        finally:
            if uploader in self._uploads:
                self._uploads.remove(uploader)

        progress.finish_task()
        return result

    def abort_uploads(self):
        for up in self._uploads:
            up.abort()

    def is_uploaded(self, checksum=None, content_checksum=None):
        assert checksum or content_checksum

        if checksum:
            data = {'checksum': checksum}
        else:
            data = {'content_checksum': content_checksum}

        result = self._call('upload/check', data=data)
        data = result.json()
        if data.get('result'):
            return True, data
        else:
            return False, None

    def upload_log(self, content):
        result = self._call('log/upload', skip_login=True, data={'log': content})
        data = result.json()
        if data['result']:
            return center.WEB + 'log/' + data['id']
        else:
            return None

    def get_team_members(self, mid):
        result = self._call('mod/team/fetch', data={'mid': mid})
        return result.json()

    def update_team_members(self, mid, members):
        result = self._call('mod/team/update', json={
            'mid': mid,
            'members': members
        })
        return result.json()

    def get_private_mods(self):
        result = self._call('mod/list_private', method='GET', timeout=20)
        return result.json()
