import sys
import os.path
import subprocess


def update():
    if sys.platform == 'win32':
        subprocess.check_call(['cmd', '/C', 'yarn'])
    else:
        subprocess.check_call(['yarn'])

    open('node_modules/stamp', 'w').close()


def main():
    if not os.path.isfile('yarn.lock'):
        print('ERROR: yarn.lock not found! Quitting...')
        sys.exit(1)

    if not os.path.isfile('node_modules/stamp'):
        print('node_modules is missing, running "yarn".')
        update()
        return

    src_time = os.stat('yarn.lock').st_mtime
    dest_time = os.stat('node_modules/stamp').st_mtime

    if src_time > dest_time:
        print('yarn.lock has changed, running "yarn".')
        update()


if __name__ == '__main__':
    main()
