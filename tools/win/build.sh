#!/bin/bash

set -e

cd "$(dirname "$0")"
PLATFORM=windows
. ../common/helpers.sh
init_build_script "$@"

if ! has wine || ! has tar || ! has 7z || ! has unzip || ! has git; then
    error "Sorry, but I need wine, tar, 7z, unzip and git to generate a windows build."
    exit 1
fi

export WINEPREFIX="$PWD/_w"
export WINEARCH="win32"
export WINEDEBUG="fixme-all"

if [ ! -d _w ]; then
    msg "Setting up toolchain..."
    msg2 "Downloading..."
    
    download python.msi "https://www.python.org/ftp/python/2.7.9/python-2.7.9.msi"
    download pywin32.exe "http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win32-py2.7.exe/download"
    download upx.zip "http://upx.sourceforge.net/download/upx391w.zip"
    download 7z-inst.exe "http://sourceforge.net/projects/sevenzip/files/7-Zip/9.20/7z920.exe/download"
    download SDL2.zip "http://libsdl.org/release/SDL2-2.0.3-win32-x86.zip"
    download openal.zip "http://kcat.strangesoft.net/openal-soft-1.16.0-bin.zip"
    download nsis.exe "http://prdownloads.sourceforge.net/nsis/nsis-2.46-setup.exe?download"
    download nsProcess.7z "https://dev.tproxy.de/mirror/nsProcess_1_6.7z"
    
    msg2 "Installing Python..."
    wine msiexec /i python.msi

    msg2 "Checking Python..."
    if ! wine python -c 'print("Works")'; then
        if [ -d _w/drive_c/Python27 ]; then
            pushd _w/drive_c/windows
            ln -s ../Python27/python.exe
            popd
            msg2 "Fixed!"
        else
            error "Python wasn't added to PATH and it was not installed in C:\Python27."
            exit 1
        fi
    fi
    
    msg2 "Installing pywin32..."
    wine pywin32.exe

    msg2 "Updating pip..."
    wine python -mpip install -U pip
    
    msg2 "Installing dependencies from PyPi..."
    wine python -mpip install six semantic_version PySide comtypes requests ndg-httpsclient pyasn1

    msg2 "Fixing ndg.httpsclient..."
    wine python -c 'import ndg.httpsclient;import os.path;open(os.path.join(ndg.httpsclient.__path__[0], "__init__.py"), "w").close()'

    ensure_pyinstaller
    
    msg2 "Unpacking upx..."
    mkdir tmp
    unzip -qd tmp upx.zip
    mv tmp/upx*/upx.exe _w/drive_c/windows
    rm -r tmp
    
    msg2 "Unpacking 7z..."
    mkdir tmp
    7z x -otmp 7z-inst.exe
    mv tmp/7z.{exe,dll} support
    rm -r tmp
    
    msg2 "Unpacking SDL..."
    unzip -q SDL2.zip SDL2.dll
    mv SDL2.dll support
    
    msg2 "Unpacking OpenAL..."
    mkdir tmp
    unzip -qd tmp openal.zip
    mv tmp/openal-soft-*/bin/Win32/soft_oal.dll support/openal.dll
    rm -r tmp

    msg2 "Installing NSIS..."
    wine nsis.exe

    msg2 "Unpacking NsProcess..."
    mkdir tmp
    7z x -otmp nsProcess.7z
    mv tmp/Plugin/*.dll _w/drive_c/Program\ Files/NSIS/Plugins
    mv tmp/Include/*.nsh _w/drive_c/Program\ Files/NSIS/Include
    rm -r tmp
    
    msg2 "Cleaning up..."
    rm python.msi pywin32.exe upx.zip 7z-inst.exe SDL2.zip openal.zip nsis.exe nsProcess.7z
fi

msg "Building..."
generate_version > version
ensure_pyinstaller

pushd ../..
make ui resources
popd

msg2 "Running PyInstaller..."
[ -d dist ] && rm -rf dist
wine python -OO ../common/pyinstaller/pyinstaller.py -y --distpath=.\\dist --workpath=.\\build Knossos.spec

mv version dist/

if [ "$gen_package" = "y" ]; then
    msg2 "Packing installer..."
    wine C:\\Program\ Files\\NSIS\\makensis /NOCD /DKNOSSOS_ROOT=..\\..\\ /DKNOSSOS_VERSION="$(cat dist/version)" nsis/installer.nsi

    msg2 "Packing updater..."
    wine C:\\Program\ Files\\NSIS\\makensis /NOCD /DKNOSSOS_ROOT=..\\..\\ /DKNOSSOS_VERSION="$(cat dist/version)" nsis/updater.nsi
fi
