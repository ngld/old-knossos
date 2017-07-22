#!/bin/bash

set -eo pipefail

echo "==> Installing build tools"
brew update
brew install python p7zip ninja qt5
pip2 install -U pip
pip2 install dmgbuild

mkdir /tmp/prov
cd /tmp/prov

# We need Python 3.5 since that's the latest version PyInstaller supports.
echo "==> Installing Python 3.5"
curl -so python.pkg "https://www.python.org/ftp/python/3.5.3/python-3.5.3-macosx10.6.pkg"
sudo installer -store -pkg python.pkg -target /

echo "==> Installing Python dependencies"
pip3 install -U pip
pip3 install six requests raven semantic_version PyQt5 PyInstaller

echo "==> Installing SDL2"
curl -so SDL2.dmg "https://libsdl.org/release/SDL2-2.0.5.dmg"

dev="$(hdiutil attach SDL2.dmg | tail -n1 | awk '{ print $3 }')"
sudo cp -a "$dev/SDL2.framework" /Library/Frameworks
hdiutil detach "$dev"

echo "==> Cleanup"
cd ..
rm -r prov
