#!/bin/bash

set -exo pipefail

if [ "$TRAVIS_OS_NAME" == "osx" ]; then
    echo "==> Installing build tools"
    brew install p7zip ninja qt5

    # If we don't delete qmake, PyInstaller detects this Qt installation and uses its libraries instead of PyQt5's
    # which then leads to a crash because PyQt5 isn't compatible with the version we install.
    sudo rm -f /usr/local/Cellar/qt/*/bin/qmake

    mkdir /tmp/prov
    cd /tmp/prov

    # We need Python 3.6 since that's the latest version PyInstaller supports.
    echo "==> Installing Python 3.6.5"
    curl -so python.pkg "https://www.python.org/ftp/python/3.6.5/python-3.6.5-macosx10.6.pkg"
    sudo installer -store -pkg python.pkg -target /

    echo "==> Installing Python dependencies"
    pip3 install -U pip
    pip3 install six requests requests_toolbelt ply raven semantic_version PyQt5 PyInstaller token_bucket dmgbuild

    echo "==> Installing SDL2"
    curl -so SDL2.dmg "https://libsdl.org/release/SDL2-2.0.8.dmg"

    dev="$(hdiutil attach SDL2.dmg | tail -n1 | awk '{ print $3 }')"
    sudo cp -a "$dev/SDL2.framework" /Library/Frameworks
    hdiutil detach "$dev"

    echo "==> Cleanup"
    cd ..
    rm -r prov
fi
