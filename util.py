import os.path
import logging
import six
import progress
from six.moves.urllib.request import urlopen


def get(link):
    try:
        logging.info('Retrieving "%s"...', link)
        result = urlopen(link)
        if six.PY2:
            code = result.getcode()
        else:
            code = result.status

        if code == 200:
            return result
        else:
            return None
    except:
        logging.exception('Failed to load "%s"!', link)

    return None


def download(link, dest):
    try:
        logging.info('Downloading "%s"...', link)
        result = urlopen(link)
        if six.PY2:
            size = float(result.info()['Content-Length'])
            if result.getcode() != 200:
                return False
        else:
            size = float(result.getheader('Content-Length'))
            if result.status != 200:
                return False

        start = dest.tell()
        while True:
            chunk = result.read(50 * 1024)  # Read 50KB chunks
            if not chunk:
                break

            dest.write(chunk)

            progress.update((dest.tell() - start) / size, '%s: %d%%' % (os.path.basename(link), 100 * (dest.tell() - start) / size))
    except:
        logging.exception('Failed to load "%s"!', link)
        return False

    return True


def normpath(path):
    return os.path.normcase(path.replace('\\', '/'))
