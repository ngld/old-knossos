#!/bin/bash

set -e
cd "$(dirname "$0")"

PLATFORM=mac
. ../common/helpers.sh

if [ "$use_buildenv" = "y" ]; then
    export PATH="$PWD/buildenv/bin:$PATH"

    if [ ! -d buildenv ]; then
        msg "Setting up a clean build environment..."
        
        mkdir buildenv
        cd buildenv

        msg2 "Installing Homebrew..."
        curl -Lo homebrew.tar.gz https://github.com/Homebrew/homebrew/tarball/master
        tar -xzf homebrew.tar.gz --strip 1
        rm homebrew.tar.gz

        cd ..
        msg2 "Installing Python, 7-zip and SDL2..."
        brew install python p7zip sdl2

        msg2 "Installing Qt..."
        msg2 "NOTE: This might take a LONG time."
        brew install qt

        msg2 "Installing virtualenv..."
        pip2 install virtualenv
    fi
else
    msg "Looking for missing dependencies..."
    if ! has brew; then
        msg3 "You don't have Homebrew!"
        answer=""
        while [ "$answer" = "" ]; do
            echo -n "Shall I install it for you? (y/n): "
            read answer

            if [ "$answer" = "n" ]; then
                msg3 "If you want to install Homebrew yourself, go to http://brew.sh"
                error "Homebrew is missing!"
                exit 1
            elif [ ! "$answer" = "y" ]; then
                echo "That's not a valid answer!"
                answer=""
            fi
        done

        ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
        brew update
        brew doctor
    fi

    if ! has python2; then
        brew install python
    fi

    if ! has 7z; then
        brew install p7zip
    fi

    if [ ! -e /usr/local/lib/libSDL2.dylib ]; then
        brew install sdl2
    fi

    if [ ! -e /usr/local/lib/QtCore.framework ]; then
        brew install qt
    fi

    if ! has virtualenv; then
        msg2 "Installing virtualenv..."
        pip2 install virtualenv
    fi
fi


if [ ! -d pyenv ]; then
    msg "Setting up my python environment..."
    virtualenv pyenv
    source pyenv/bin/activate

    msg2 "Installing Python packages..."
    pip install six semantic_version PySide requests ndg-httpsclient pyasn1 dmgbuild

    msg2 "Fixing ndg.httpsclient..."
    python -c 'import ndg.httpsclient;import os.path;open(os.path.join(ndg.httpsclient.__path__[0], "__init__.py"), "w").close()'
else
    source pyenv/bin/activate
fi

ensure_pyinstaller

msg "Building..."
generate_version > version

msg2 "Running PyInstaller..."
[ -d dist ] && rm -rf dist

# Make sure PyInstaller finds libpyside-*.dylib and the Qt libraries.
if [ "$use_buildenv" = "y" ]; then
    export QTDIR="buildenv/lib"
else
    export QTDIR="/usr/local/lib"
fi

export DYLD_FRAMEWORK_PATH="$QTDIR"
export DYLD_LIBRARY_PATH="pyenv/lib/python2.7/site-packages/PySide"

python -OO ../common/pyinstaller/pyinstaller.py -y --distpath=./dist --workpath=./build  Knossos.spec

if [ "$gen_package" = "y" ]; then
    msg "Packing DMG..."
    size="$(du -sm dist/Knossos.app | awk '{ print $1 }')"
    size=$(($size + 2))

    # dmgbuild needs the Quartz module. To avoid recompiling it, we use the installed version.
    if [ ! -e PyObjC ]; then
        ln -s /System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/PyObjC .
    fi
    PYTHONPATH="PyObjC" dmgbuild -s dmgbuild_cfg.py -Dsize="${size}M" Knossos dist/Knossos.dmg
fi

msg "Done!"
