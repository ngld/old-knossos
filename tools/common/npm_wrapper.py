import sys
import os.path
import subprocess


def update():
    subprocess.check_call(['npm', 'install'])

    open('node_modules/stamp', 'w').close()


def main():
    if not os.path.isfile('package.json'):
        print('ERROR: package.json not found! Quitting...')
        sys.exit(1)

    if not os.path.isfile('node_modules/stamp'):
        print('node_modules is missing, running "npm install".')
        update()
        return

    src_time = os.stat('package.json').st_mtime
    dest_time = os.stat('node_modules/stamp').st_mtime

    if src_time > dest_time:
        print('package.json has changed, running "npm install".')
        update()


if __name__ == '__main__':
    main()
