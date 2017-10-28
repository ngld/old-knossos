#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager .
rsync -a --exclude=releng --exclude=node_modules src/ work/

if [ ! -d src/releng/ubuntu/cache ]; then
	mkdir -p src/releng/ubuntu/cache
fi

cd src/releng/ubuntu/cache
cp ../../../package.json .
npm install
npm install es6-shim

cd ../../../../work

export QT_SELECT=5

rsync -au ../src/releng/ubuntu/cache/node_modules/ node_modules/
python3 configure.py
ninja resources

export KN_DEBUG=1
#gdb --args python3 knossos/__main__.py
python3 knossos/__main__.py
