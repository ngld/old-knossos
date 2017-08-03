#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager .
rsync -a --exclude=releng src/ work/
cd work

export QT_SELECT=5

python3 configure.py
ninja resources

export KN_DEBUG=1
#gdb --args python3 knossos/__main__.py
python3 knossos/__main__.py
