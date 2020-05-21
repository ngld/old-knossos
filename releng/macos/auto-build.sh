#!/bin/bash

set -e

export PATH="/usr/local/bin:$HOME/.yarn/bin:$HOME/.config/yarn/global/node_modules/.bin:$PATH:/Library/Frameworks/Python.framework/Versions/3.6/bin:/usr/local/opt/qt5/bin"
export LANG="en_US.UTF-8"

# ninja ends up in a reconfigure loop here without this
export SKIP_RECONF=1

cd "$(dirname "$0")"
rm -rf dist/*

cd ../..

echo "==> Installing NPM modules"
python3 tools/common/npm_wrapper.py

echo "==> Configuring..."
python3 configure.py

echo "==> Building..."
ninja dmg
