import logging
import re
import time
import json
from threading import Lock

from lib import util

MEDIAFIRE_CHECK = re.compile(r'^https?://(www\.)?mediafire\.com/(\?[a-z|0-9]+|download/.*)$')
MEDIAFIRE_EXTRACT = re.compile(r'kNO = "(http://[^"]+)"')

FSMODS_CHECK = re.compile(r'^https?://(?:www\.)(?:fsmods|freespacemods)\.net/(download\.php\?view\.|request\.php\?)([0-9]+)$')
ASK_USER = None
ASK_LOCK = Lock()


class FsMods(object):

    @staticmethod
    def supports(link):
        return FSMODS_CHECK.match(link)

    @staticmethod
    def process(link, dest):
        info = FSMODS_CHECK.match(link)
        dl_link = 'http://www.freespacemods.net/request.php?' + info.group(2)
        info_link = 'http://www.freespacemods.net/download.php?view.' + info.group(2)

        with open(dest, 'wb') as stream:
            return util.download(dl_link, stream, headers={'Referer': info_link})


class MediaFire(object):

    @staticmethod
    def supports(link):
        return MEDIAFIRE_CHECK.match(link)

    @staticmethod
    def process(link, dest):
        tries = 3

        while tries > 0:
            if tries < 3:
                time.sleep(0.3)

            tries -= 1

            with open(dest, 'wb') as stream:
                res = util.download(link, stream, random_ua=True)

            if not res:
                return False
            
            with open(dest, 'r') as stream:
                if '<html' not in stream.read(1024):
                    # Let's assume we downloaded the file.
                    return True

                stream.seek(0)
                data = stream.read()
                break

        tries += 1

        while tries > 0:
            if tries < 3:
                time.sleep(0.3)
            
            tries -= 1

            if 'solvemedia.com/papi/' in data:
                logging.info('Detected SolveMedia captcha in "%s".', link)
                try:
                    sv = SolveMedia(data)
                    code = sv.get_code()
                    challenge = sv.get_challenge(code)
                except:
                    logging.exception('Captcha solving failed!')
                else:
                    data = {
                        'adcopy_challenge': challenge,
                        'adcopy_response': code.replace(' ', '+')
                    }

                    data = util.get(link, data=data, random_ua=True).read().decode('utf8', 'replace')
                    if not data:
                        logging.error('Failed to submit captcha response!')
            elif re.search(r'(api\.recaptcha\.net|google\.com/recaptcha/api/)', data):
                logging.info('Detected ReCaptcha in "%s".', link)

                try:
                    rc = ReCaptcha(data)
                    info = re.search(r'challenge\?k=(.+?)"', data)
                    if info:
                        rc.id_ = info.group(1)
                        rc.ask_for_code(link)
                        data = rc.data
                    else:
                        logging.error('Can\'t find the ReCaptcha challenge!')
                except:
                    logging.exception('Captcha solving failed!')
            else:
                info = MEDIAFIRE_EXTRACT.search(data)
                if not info:
                    logging.error('Failed to parse MediaFire\'s response! Probably a CAPTCHA...')
                    continue
                else:
                    with open(dest, 'wb') as stream:
                        return util.download(info.group(1), stream, random_ua=True)


class CaptchaSolver(object):
    captcha_address = None

    def get_code(self, image=None):
        global ASK_USER

        if image is None:
            image = self.captcha_address

        if ASK_USER is None:
            logging.warning('Sorry, CAPTCHA solving is not supported under these circumstances!')
            return None
        else:
            return ASK_USER(image)


class SolveMedia(CaptchaSolver):
    data = None
    challenge = None
    chId = None
    path = None
    secure = False
    noscript = True

    def __init__(self, data):
        self.data = data

        self.load()
        self.captcha_address = self.captcha_address.replace('%0D%0A', '').strip()

    def load(self):
        self.get_challenge_key()

        if self.secure:
            server = 'http://api.solvemedia.com'
        else:
            server = 'https://api-secure.solvemedia.com'

        path = '/papi/challenge.noscript?k='
        
        self.path = server + path + self.challenge
        self.data = util.get(self.path, random_ua=True).read().decode('utf8', 'replace')

        if '>error: domain / ckey mismatch' in self.data:
            raise Exception('Domain / ckey mismatch')

        captcha_address = re.search(r'<img src="(/papi/media\?c=[^"]+)', self.data)
        if not captcha_address:
            captcha_address = re.search(r'src="(/papi/media\?c=[^"]+)', self.data)
        
        if captcha_address is None:
            raise Exception('Failed SolveMedia')
        else:
            self.captcha_address = captcha_address
                
    def get_challenge_key(self):
        challenge = re.search(r'http://api\.solvemedia\.com/papi/_?challenge\.script\?k=(.{32})', self.data)
        if challenge is None:
            challenge = re.search(r'<input type=hidden name="k" value="([^"]+)">', self.data)

        if challenge is None:
            self.secure = True
            challenge = re.search(r'ckey:\'([\w-\.]+)\'', self.data)
            if challenge is None:
                challenge = re.search(r'https://api\-secure\.solvemedia\.com/papi/_?challenge\.script\?k=(.{32})', self.data)

            if challenge is None:
                self.secure = False

        if challenge is not None:
            challenge = challenge.group(1)
        self.challenge = challenge

    def get_challenge(self, code):
        data = {}
        for find in re.findall(r'<input type=hidden name="([^"]+)" value="([^"]+)">'):
            data[find[0]] = find[1]

        data['adcopy_response'] = code
        
        url = self.path
        url = url[:url.find('media?c=')] + 'verify.noscript'
        data = util.get(url, data=data, random_ua=True).read().decode('utf8', 'replace')
        
        if not data:
            logging.error('Failed to submit challenge!')
            return None

        info = re.search(r'URL=(http[^"]+)')
        if not info:
            return None

        url = info.group(1)

        if self.secure:
            url = url.replace('http://', 'https://')

        data = util.get(url, random_ua=True)
        if data:
            return re.search(r'id=gibberish>([^<]+)', data).group(1)
        else:
            return None


class ReCaptcha(CaptchaSolver):
    MAX_TRIES = 5
    challenge = None
    id_ = None
    tries = 0
    server = None
    data = None

    def __init__(self, data):
        self.data = data

    def reload(self):
        data = util.get('http://www.google.com/recaptcha/api/reload?c=' + self.challenge + '&k=' + self.id_ + '&reason=r&type=image&lang=en')
        if not data:
            return False

        data = data.read().decode('utf8')
        challenge = re.search(r'Recaptcha\.finish\_reload\(\'(.*?)\', \'image\'')
        if not challenge:
            raise Exception('Failed to reload captcha!')

        self.captcha_address = self.server + 'image?c=' + self.challenge

    def ask_for_code(self, link):
        data = util.get('http://api.recaptcha.net/challenge?k=' + self.id_).read().decode('utf8', 'replace')
        challenge = re.search(r'challenge.*?:.*?\'(.*)?\',', data)
        server = re.search(r'server.*?:.*?\'(.*?)\',', data)

        if not challenge or not server:
            raise Exception('Failed to get ReCaptcha API response')
        
        self.challenge = challenge.group(1)
        self.server = server.group(1)
        self.captcha_address = self.server + 'image?c=' + self.challenge
        
        while self.tries < self.MAX_TRIES:
            if self.tries > 0:
                self.reload()

            code = self.get_code()

            if not self.challenge or not code:
                raise Exception('Invalid challenge or code!')

            data = {
                'recaptcha_challenge_field': self.challenge,
                'recaptcha_response_field': code
            }

            self.tries += 1
            self.data = util.get(link, data=data, random_ua=True).read().decode('utf8', 'replace')

            info = re.search(r'challenge\?k=(.+?)"')
            if not info:
                # No ID found \o/
                break

            self.id_ = info.group(1).replace('&amp;error=1', '')


strategies = (FsMods, MediaFire)


def download(link, dest):
    for strat in strategies:
        if strat.supports(link):
            return strat.process(link, dest)

    return None


def is_direct(link):
    for strat in strategies:
        if strat.supports(link):
            return False

    return True


def init_ws_mode(ws):
    global ASK_USER

    def asker(image):
        global ASK_LOCK

        # Only one question at a time.
        with ASK_LOCK:
            ws.send(json.dumps(('captcha', image)))

            # Wait a minute for user response.
            wait = time.time() + 60
            resp = None
            while not resp and time.time() < wait:
                resp = ws.recv_nb()

                if not resp:
                    time.sleep(0.3)
                else:
                    resp = resp.decode('utf8', 'replace')

            return resp

    ASK_USER = asker


def finish_mode():
    global ASK_USER

    ASK_USER = None
