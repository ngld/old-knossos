import os.path
import logging
import requests

from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from . import center, progress, util


class InvalidLoginException(Exception):
    pass


class RequestFailedException(Exception):
    pass


class AccessDeniedException(RequestFailedException):
    pass


class NebulaClient(object):
    _token = None
    _sess = None

    def __init__(self):
        self._sess = requests.Session()

    def _call(self, path, method='POST', skip_login=False, check_code=False, **kwargs):
        url = center.settings['nebula_link'] + path

        if not skip_login and not self._token:
            if not self.login():
                raise InvalidLoginException()

        if self._token:
            headers = kwargs.setdefault('headers', {})
            headers['X-KN-TOKEN'] = self._token

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

        return result

    def login(self, user=None, password=None):
        if not user:
            user = center.settings['neb_user']
            password = center.settings['neb_password']

        result = self._call('login', skip_login=True, data={
            'user': user,
            'password': password
        })

        if result.status_code != 200:
            return False

        data = result.json()
        if data['result']:
            self._token = data['token']
            return True
        else:
            return False

    def register(self, user, password, email):
        self._call('register', skip_login=True, check_code=True, data={
            'name': user,
            'password': password,
            'email': email
        })

        return True

    def reset_password(self, user):
        self._call('reset_password', skip_login=True, check_code=True, data={'user': user})
        return True

    def get_editable_mods(self):
        result = self._call('mod/editable', 'GET', check_code=True)
        return result.json()['mods']

    def _upload_mod_logos(self, mod):
        chks = [None, None]

        for i, prop in enumerate(('logo', 'tile')):
            im = getattr(mod, prop)
            if im and os.path.isfile(im):
                chks[i] = util.gen_hash(im)[1]
                self.upload_file(prop, im)

        return chks

    def check_mod_id(self, mid, title=None):
        result = self._call('mod/check_id', check_code=True, data={
            'id': mid,
            'title': title
        })

        return result.json()['result']

    def create_mod(self, mod):
        logo_chk, tile_chk = self._upload_mod_logos(mod)

        self._call('mod/create', check_code=True, json={
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

        self._call('mod/update', check_code=True, json={
            'id': mod.mid,
            'title': mod.title,
            'logo': logo_chk,
            'tile': tile_chk,
            'first_release': mod.first_release.strftime('%Y-%m-%d') if mod.first_release else None,
            'members': [center.settings['neb_user']]
        })
        return True

    def preflight_release(self, mod):
        meta = mod.get()
        meta['screenshots'] = []
        meta['attachments'] = []
        meta['banner'] = ''

        result = self._call('mod/release/preflight', check_code=True, json=meta)
        data = result.json()
        if not data:
            raise RequestFailedException()

        if data['result']:
            return True

        if data.get('reason') == 'unauthorized':
            raise AccessDeniedException()

        raise RequestFailedException(data.get('reason'))

    def _prepare_release(self, mod):
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

        return meta

    def create_release(self, mod):
        meta = self._prepare_release(mod)
        result = self._call('mod/release', check_code=True, json=meta)
        data = result.json()
        if not data:
            raise RequestFailedException('unknown')

        if data['result']:
            return True

        if data.get('reason') == 'unauthorized':
            raise AccessDeniedException(data['reason'])

        raise RequestFailedException(data.get('reason'))

    def update_release(self, mod):
        meta = self._prepare_release(mod)
        result = self._call('mod/release/update', check_code=True, json=meta)
        data = result.json()
        if not data:
            raise RequestFailedException('unknown')

        if data['result']:
            return True

        if data.get('reason') == 'unauthorized':
            raise AccessDeniedException(data['reason'])

        raise RequestFailedException(data.get('reason'))

    def report_release(self, mod, message):
        result = self._call('mod/release/report', check_code=True, data={
            'mid': mod.mid,
            'version': str(mod.version),
            'message': message
        })
        data = result.json()
        if not data or not data.get('result'):
            raise RequestFailedException('unknown')

        return True

    def delete_release(self, mod):
        result = self._call('mod/release/delete', check_code=True, data={
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

    def upload_file(self, name, path, fn=None, content_checksum=None):
        _, checksum = util.gen_hash(path)

        result = self._call('upload/check', check_code=True, data={'checksum': checksum})
        data = result.json()
        if data.get('result'):
            # Already uploaded
            return True

        hdl = open(path, 'rb')
        enc = MultipartEncoder({
            'checksum': checksum,
            'content_checksum': content_checksum,
            'file': ('upload', hdl, 'application/octet-stream')
        })

        enc_len = enc.len

        def cb(monitor):
            progress.update(monitor.bytes_read / enc_len, 'Uploading %s...' % name)

        monitor = MultipartEncoderMonitor(enc, cb)
        self._call('upload/file', data=monitor, headers={
            'Content-Type': monitor.content_type
        }, check_code=True)

        return True

    def is_uploaded(self, checksum=None, content_checksum=None):
        assert checksum or content_checksum

        if checksum:
            data = {'checksum': checksum}
        else:
            data = {'content_checksum': content_checksum}

        result = self._call('upload/check', check_code=True, data=data)
        data = result.json()
        if data.get('result'):
            return True, data
        else:
            return False, None
