#!/bin/bash

set -e

cd "$(dirname "$0")"
cd ../..

rm -rf node_modules
cp -r /opt/knossos-prov/node_modules .

echo "==> Configuring..."
python2.7 configure.py

echo "==> Building..."
ninja dist
