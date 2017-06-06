#!/bin/bash

set -e

export PATH="/usr/local/bin:$PATH"
export LANG="en_US.UTF-8"

cd "$(dirname "$0")"
cd ../..

echo "==> Configuring..."
PATH="$PATH:/usr/local/opt/qt5/bin" python3 configure.py

echo "==> Building..."
ninja dmg
