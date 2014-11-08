#!/bin/bash

set -e
cd "$(dirname "$0")"
export PATH="$PWD/buildenv/bin:$PATH"

PLATFORM=mac
. ../common/helpers.sh

while [ ! "$1" = "" ]; do
    case "$1" in
        -h|--help)
            echo "Usage: $(basename "$0") [build variant]"
            exit 0
        ;;
        *)
            if [ "$VARIANT" = "" ]; then
                VARIANT="$1"
            else
                error "You passed an invalid option \"$1\". I don't know what to do with that..."
                exit 1
            fi
        ;;
    esac
    shift
done

check_variant

if [ ! -d buildenv ]; then
    msg "Setting up a clean build environment..."
    
    mkdir buildenv
    cd buildenv

    msg2 "Installing Homebrew..."
    curl -Lo homebrew.tar.gz https://github.com/Homebrew/homebrew/tarball/master
    tar -xzf homebrew.tar.gz --strip 1
    rm homebrew.tar.gz

    cd ..
    msg2 "Installing Python, 7-zip, SDL2 and UPX..."
    brew install python p7zip sdl2 upx

    msg2 "Installing Qt..."
    msg2 "NOTE: This might take a LONG time."
    brew install --without-docs qt

    msg2 "Installing virtualenv..."
    pip2 install virtualenv
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
[ -d dist ] && rm -r dist

# Make sure PyInstaller find libpyside-*.dylib and the Qt libraries.
export QTDIR="buildenv/lib"
export DYLD_FRAMEWORK_PATH="$QTDIR"
export DYLD_LIBRARY_PATH="py/lib/python2.7/site-packages/PySide"

python -OO ../common/pyinstaller/pyinstaller.py -y Knossos.spec

msg "Packing DMG..."
size="$(du -cm dist/Knossos.app | awk '{ print $1 }')"
size=$(($size + 2))

# dmgbuild needs the Quartz module. To avoid recompiling it, we use the installed version.
if [ ! -e PyObjC ]; then
    ln -s /System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/PyObjC .
fi
PYTHONPATH="PyObjC" dmgbuild -s dmgbuild_cfg.py -Dsize="${size}M" Knossos Knossos.dmg

msg "Done!"
