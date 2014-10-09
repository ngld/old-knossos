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

export WINEPREFIX="$PWD/_w"
export WINEARCH="win32"
export WINEDEBUG="fixme-all"

if [ ! -d _w ]; then
    echo "Setting up toolchain..."
    echo "==> Downloading..."
    
    download python.msi "https://www.python.org/ftp/python/2.7.8/python-2.7.8.msi"
    download pywin32.exe "http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win32-py2.7.exe/download"
    download get-pip.py "https://bootstrap.pypa.io/get-pip.py"
    download pyinstaller.tar.gz "https://github.com/pyinstaller/pyinstaller/releases/download/v2.1/PyInstaller-2.1.tar.gz"
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
    wine python -mpip install six semantic_version PySide
    
    echo "==> Unpacking PyInstaller..."
    tar -xzf pyinstaller.tar.gz
    
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
    rm python.msi pywin32.exe get-pip.py pyinstaller.tar.gz 7z-inst.exe SDL.zip openal.zip nsis.exe nsProcess.7z
fi

echo "Building..."
git log | head -1 | cut -d " " -f 2 | cut -b -7 > ./commit

wine python -OO PyInstaller-*/pyinstaller.py -y Knossos.spec

echo "Packing installer..."
wine C:\\Program\ Files\\NSIS\\makensis /NOCD /DKNOSSOS_ROOT=..\\ nsis/installer.nsi

echo "Packing updater..."
wine C:\\Program\ Files\\NSIS\\makensis /NOCD /DKNOSSOS_ROOT=..\\ nsis/updater.nsi
