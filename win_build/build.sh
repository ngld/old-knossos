#!/bin/bash

has() {
    which "$@" > /dev/null 2>&1
}

download() {
    if has wget; then
        wget -O "$1" "$2"
    elif has curl; then
        curl -# -o "$1" "$2"
    else
        echo "I need curl or wget!"
        exit 1
    fi
}

if ! has wine || ! has tar || ! has 7z || ! has unzip; then
    echo "Sorry, but I need wine, tar, 7z and unzip to generate a windows build."
    exit 1
fi

cd "$(dirname "$0")"

variant="$1"

if [ -z "$variant" ]; then
    variant="develop"
    echo "No variant specified. Assuming $variant."
fi

update_server="https://dev.tproxy.de/knossos/${variant}"

export WINEPREFIX="$PWD/_w"
export WINEARCH="win32"
export WINEDEBUG="fixme-all"

if [ ! -d _w ]; then
    echo "Setting up toolchain..."
    echo "==> Downloading..."
    
    download python.msi "https://www.python.org/ftp/python/2.7.8/python-2.7.8.msi"
    download pywin32.exe "http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win32-py2.7.exe/download"
    download get-pip.py "https://bootstrap.pypa.io/get-pip.py"
    download upx.zip "http://upx.sourceforge.net/download/upx391w.zip"
    download 7z-inst.exe "http://sourceforge.net/projects/sevenzip/files/7-Zip/9.22/7z922.exe/download"
    download SDL.zip "http://libsdl.org/release/SDL-1.2.15-win32.zip"
    download openal.zip "http://kcat.strangesoft.net/openal-soft-1.16.0-bin.zip"
    download nsis.exe "http://prdownloads.sourceforge.net/nsis/nsis-2.46-setup.exe?download"
    download nsProcess.7z "http://dev.tproxy.de/mirror/nsProcess_1_6.7z"
    
    echo "==> Installing Python..."
    wine msiexec /i python.msi
    
    echo "==> Installing pywin32..."
    wine pywin32.exe
    
    echo "==> Installing pip..."
    wine python get-pip.py
    
    echo "==> Installing dependencies from PyPi..."
    wine python -mpip install six semantic_version PySide comtypes requests ndg-httpsclient pyasn1

    echo "==> Fixing ndg.httpsclient..."
    wine python -c 'import ndg.httpsclient;import os.path;open(os.path.join(ndg.httpsclient.__path__[0], "__init__.py"), "w").close()'
    
    echo "==> Cloning PyInstaller..."
    git clone "https://github.com/pyinstaller/pyinstaller.git"
    
    echo "==> Unpacking upx..."
    unzip upx.zip
    mv upx*/upx.exe _w/drive_c/windows
    rm -r upx*
    
    echo "==> Unpacking 7z..."
    mkdir tmp
    7z x -otmp 7z-inst.exe
    mv tmp/7z.{exe,dll} .
    rm -r tmp
    
    echo "==> Unpacking SDL..."
    unzip -o SDL.zip SDL.dll
    
    echo "==> Unpacking OpenAL..."
    unzip openal.zip
    mv openal-soft-*/bin/Win32/soft_oal.dll openal.dll
    rm -r openal-soft-*

    echo "==> Installing NSIS..."
    wine nsis.exe

    echo "==> Unpacking NsProcess..."
    mkdir tmp
    7z x -otmp nsProcess.7z
    mv tmp/Plugin/*.dll _w/drive_c/Program\ Files/NSIS/Plugins
    mv tmp/Include/*.nsh _w/drive_c/Program\ Files/NSIS/Include
    rm -r tmp
    
    echo "==> Cleaning up..."
    rm python.msi pywin32.exe get-pip.py 7z-inst.exe SDL.zip openal.zip nsis.exe nsProcess.7z
fi

echo "Building..."
last_version="$(curl -s "${update_server}/version")"
my_version="$(grep VERSION ../knossos/center.py | cut -d "'" -f 2)"

last_vnum="$(echo "$last_version" | cut -d '-' -f 1)"
my_vnum="$(echo "$my_version" | cut -d '-' -f 1)"

if [ "$last_vnum" = "$my_vnum" ]; then
    build_num="$(echo "$last_version" | cut -d '-' -f 2 | cut -d . -f 2)"
    build_num=$(( $build_num + 1 ))
else
    build_num="0"
fi

if [ "$variant" = "develop" ]; then
    commit="$(git log | head -1 | cut -d " " -f 2 | cut -b -7)"
    next_version="${my_version}.${build_num}+${commit}"
else
    if [ ! "$build_num" = "0" ]; then
        echo "ERROR: This version has already been released!"
        exit 1
    fi
fi

echo "$next_version" > version
wine python -OO pyinstaller/pyinstaller.py -y Knossos.spec

echo "Packing installer..."
wine C:\\Program\ Files\\NSIS\\makensis /NOCD /DKNOSSOS_ROOT=..\\ nsis/installer.nsi

echo "Packing updater..."
wine C:\\Program\ Files\\NSIS\\makensis /NOCD /DKNOSSOS_ROOT=..\\ nsis/updater.nsi
