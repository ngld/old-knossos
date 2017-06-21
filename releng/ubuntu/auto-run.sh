#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager .
rsync -a --exclude=dist --exclude=build --exclude=packer --exclude=.vagrant src/ work/
cd work

export QT_SELECT=5

echo "Installing Babel..."
rm -rf node_modules
cp -r /build/node_modules .

python3 configure.py
exec ninja debug
