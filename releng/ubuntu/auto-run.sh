#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager .

if [ -d work ]; then
    cd work
    git reset --hard
    git pull
    cd ..
else
    git clone src work
fi

cd src
git diff > ../work/pp
cd ../work
git apply pp
rm pp

export QT_SELECT=5

python3 tools/common/npm_wrapper.py
python3 configure.py
ninja resources

export KN_DEBUG=1
#gdb --args python3 knossos/__main__.py
python3 knossos/__main__.py
