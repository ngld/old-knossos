#!/bin/bash

set -e

cd "$(dirname "$0")"
PLATFORM=windows
. ../common/helpers.sh

if ! has wine || ! has tar || ! has 7z || ! has unzip || ! has git; then
    error "Sorry, but I need wine, tar, 7z, unzip and git to generate a windows build."
    exit 1
fi

v_set=n
while [ ! "$1" = "" ]; do
    case "$1" in
        -h|--help)
            echo "Usage: $(basename "$0") [build variant]"
            exit 0
        ;;
        *)
            if [ "$v_set" = "n" ]; then
                VARIANT="$1"
                v_set=y
            else
                error "You passed an invalid option \"$1\". I don't know what to do with that..."
                exit 1
            fi
        ;;
    esac
    shift
done
unset v_set

check_variant

export WINEPREFIX="$PWD/_w"
export WINEARCH="win32"
export WINEDEBUG="fixme-all"

if [ ! -d _w ]; then
    msg "Setting up toolchain..."
    msg2 "Downloading..."
    
    download python.msi "https://www.python.org/ftp/python/2.7.8/python-2.7.8.msi"
    download pywin32.exe "http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win32-py2.7.exe/download"
    download get-pip.py "https://bootstrap.pypa.io/get-pip.py"
    download upx.zip "http://upx.sourceforge.net/download/upx391w.zip"
    download 7z-inst.exe "http://sourceforge.net/projects/sevenzip/files/7-Zip/9.22/7z922.exe/download"
    download SDL.zip "http://libsdl.org/release/SDL-1.2.15-win32.zip"
    download openal.zip "http://kcat.strangesoft.net/openal-soft-1.16.0-bin.zip"
    download nsis.exe "http://prdownloads.sourceforge.net/nsis/nsis-2.46-setup.exe?download"
    download nsProcess.7z "http://dev.tproxy.de/mirror/nsProcess_1_6.7z"
    
    msg2 "Installing Python..."
    wine msiexec /i python.msi

    msg2 "Checking Python..."
    if ! wine python -c 'print("Works")'; then
        if [ -d _w/drive_c/Python27 ]; then
            pushd _w/drive_c/windows > /dev/null
            ln -s ../Python27/python.exe
            popd > /dev/null
            msg2 "Fixed!"
        else
            error "Python wasn't added to PATH and it was not installed in C:\Python27."
            exit 1
        fi
    fi
    
    msg2 "Installing pywin32..."
    wine pywin32.exe
    
    msg2 "Installing pip..."
    wine python get-pip.py
    
    msg2 "Installing dependencies from PyPi..."
    wine python -mpip install six semantic_version PySide comtypes requests ndg-httpsclient pyasn1

    msg2 "Fixing ndg.httpsclient..."
    wine python -c 'import ndg.httpsclient;import os.path;open(os.path.join(ndg.httpsclient.__path__[0], "__init__.py"), "w").close()'

    ensure_pyinstaller
    
    msg2 "Unpacking upx..."
    unzip upx.zip
    mv upx*/upx.exe _w/drive_c/windows
    rm -r upx*
    
    msg2 "Unpacking 7z..."
    mkdir tmp
    7z x -otmp 7z-inst.exe
    mv tmp/7z.{exe,dll} .
    rm -r tmp
    
    msg2 "Unpacking SDL..."
    unzip -o SDL.zip SDL.dll
    
    msg2 "Unpacking OpenAL..."
    unzip openal.zip
    mv openal-soft-*/bin/Win32/soft_oal.dll openal.dll
    rm -r openal-soft-*

    msg2 "Installing NSIS..."
    wine nsis.exe

    msg2 "Unpacking NsProcess..."
    mkdir tmp
    7z x -otmp nsProcess.7z
    mv tmp/Plugin/*.dll _w/drive_c/Program\ Files/NSIS/Plugins
    mv tmp/Include/*.nsh _w/drive_c/Program\ Files/NSIS/Include
    rm -r tmp
    
    msg2 "Cleaning up..."
    rm python.msi pywin32.exe get-pip.py 7z-inst.exe SDL.zip openal.zip nsis.exe nsProcess.7z
fi

msg "Building..."
generate_version > version
ensure_pyinstaller

msg2 "Running PyInstaller..."
wine python -OO ../common/pyinstaller/pyinstaller.py -y Knossos.spec

msg2 "Packing installer..."
wine C:\\Program\ Files\\NSIS\\makensis /NOCD /DKNOSSOS_ROOT=..\\..\\ nsis/installer.nsi

msg2 "Packing updater..."
wine C:\\Program\ Files\\NSIS\\makensis /NOCD /DKNOSSOS_ROOT=..\\..\\ nsis/updater.nsi
