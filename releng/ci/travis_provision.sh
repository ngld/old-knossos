#!/bin/bash

set -exo pipefail
base="$(pwd)"

if [ "$TRAVIS_OS_NAME" == "osx" ]; then
    DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
    cd "${DIR}"/../macos

    source ./functions.sh

    install_yarn

    install_brews

    # If we don't delete qmake, PyInstaller detects this Qt installation and uses its libraries instead of PyQt5's
    # which then leads to a crash because PyQt5 isn't compatible with the version we install.
    sudo rm -f /usr/local/Cellar/qt/*/bin/qmake

    mkdir /tmp/prov
    cd /tmp/prov

    install_SDL2

    # install_qt5

    install_python

    echo "==> Cleanup"
    cd "${base}"
    rm -r /tmp/prov

    install_pideps

    # Make sure our macOS dependencies are installed correctly.
    # I should update the Pipfile to do this properly. However, I need a Mac for that
    # and I don't have access to one right now.
    pip3 install -U PyInstaller dmgbuild
fi
