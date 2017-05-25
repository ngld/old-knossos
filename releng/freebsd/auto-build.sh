#!/bin/bash

set -e

cd "$(dirname "$0")"
cd ../..

echo "==> Configuring..."
python2.7 configure.py

echo "==> Building..."
ninja dist
