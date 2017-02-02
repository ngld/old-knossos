#!/bin/bash
## Copyright 2015 Knossos authors, see NOTICE file
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

set -e
cd "$(dirname "$0")"

PLATFORM=mac
. ../common/helpers.sh
init_build_script "$@"

if [ "$use_buildenv" = "y" ]; then
    export PATH="$PWD/buildenv/bin:$PATH"

    if [ ! -d buildenv ]; then
        msg "Setting up a clean build environment..."
        
        mkdir buildenv
        cd buildenv

        msg2 "Installing Homebrew..."
        git clone https://github.com/Homebrew/homebrew.git
        
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
    pip install six semantic_version PySide requests dmgbuild
else
    source pyenv/bin/activate
fi

# Make sure python finds libpyside-*.dylib and libshiboken-*.dylib.
export DYLD_LIBRARY_PATH="$(python -c 'import os.path, PySide; print(os.path.dirname(PySide.__file__))')"
ensure_pyinstaller

msg "Building..."
generate_version > version

pushd ../..
make ui resources
popd

msg2 "Running PyInstaller..."
[ -d dist ] && rm -rf dist

# Make sure PyInstaller finds the Qt libraries.
if [ "$use_buildenv" = "y" ]; then
    export QTDIR="buildenv/lib"
else
    export QTDIR="/usr/local/lib"
fi

export DYLD_FRAMEWORK_PATH="$QTDIR"

python -OO ../common/pyinstaller/pyinstaller.py -y --distpath=./dist --workpath=./build Knossos.spec

# Fix the symlinks in dist/Knossos.app/Contents/MacOS
for item in ./dist/Knossos.app/Contents/MacOS/*; do
    if [ -L "$item" ]; then
        dest="$(readlink "$item" | sed 's#dist/Knossos.app/Contents#../#')"

        unlink "$item"
        ln -s "$dest" "$item"
    fi
done

if [ "$gen_package" = "y" ]; then
    if [ "$KN_BUILD_DEBUG" = "yes" ]; then
        msg "Packing archive..."

        pushd dist
        tar -czf Knossos.tar.gz Knossos
        popd
    else
        msg "Packing DMG..."
        size="$(du -sm dist/Knossos.app | awk '{ print $1 }')"
        size=$(($size + 2))

        # dmgbuild needs the Quartz module. To avoid recompiling it, we use the installed version.
        if [ ! -e PyObjC ]; then
            ln -s /System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/PyObjC .
        fi
        PYTHONPATH="PyObjC" dmgbuild -s dmgbuild_cfg.py -Dsize="${size}M" Knossos dist/Knossos.dmg
    fi
fi
msg "Done!"
