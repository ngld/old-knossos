import sys
import os.path
import subprocess


def update():
    subprocess.check_call([sys.executable, '-mpipenv', 'install'])

    open('Pipfile.stamp', 'w').close()


def main():
    if not os.path.isfile('Pipfile.lock'):
        print('ERROR: Pipfile.lock not found! Quitting...')
        sys.exit(1)

    if not os.path.isfile('Pipfile.stamp'):
        print('Pipfile.stamp is missing, running "pipenv install".')
        update()
        return

    src_time = os.stat('Pipfile.lock').st_mtime
    dest_time = os.stat('Pipfile.stamp').st_mtime

    if src_time > dest_time:
        print('Pipfile.stamp has changed, running "pipenv install".')
        update()


if __name__ == '__main__':
    main()
