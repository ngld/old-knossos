#!/bin/bash

set -e

export PATH="/usr/local/bin:$PATH:/Library/Frameworks/Python.framework/Versions/2.7/bin"
export LANG="en_US.UTF-8"

cd "$(dirname "$0")"
rm -rf dist/*

cd ../..

echo "==> Installing NPM modules"
npm install

echo "==> Configuring..."
PATH="$PATH:/usr/local/opt/qt5/bin" python3 configure.py

echo "==> Building..."
ninja dmg
