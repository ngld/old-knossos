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
    
    download python.msi "http://python.org/ftp/python/2.7.6/python-2.7.6.msi"
    download pywin32.exe "http://sourceforge.net/projects/pywin32/files/pywin32/Build%20218/pywin32-218.win32-py2.7.exe/download"
    download pyside.exe "http://download.qt-project.org/official_releases/pyside/PySide-1.2.1.win32-py2.7.exe"
    # download pyside.exe "http://sourceforge.net/projects/pyqt/files/PyQt4/PyQt-4.10.3/PyQt4-4.10.3-gpl-Py2.7-Qt4.8.5-x32.exe/download"
    download get-pip.py "https://raw.github.com/pypa/pip/master/contrib/get-pip.py"
    download pyinstaller.tar.gz "https://pypi.python.org/packages/source/P/PyInstaller/PyInstaller-2.1.tar.gz"
    download upx.zip "http://upx.sourceforge.net/download/upx391w.zip"
    download 7z-inst.exe "http://downloads.sourceforge.net/sevenzip/7z920.exe"
    download SDL.zip "http://libsdl.org/release/SDL-1.2.15-win32.zip"
    download openal.zip "http://kcat.strangesoft.net/openal-soft-1.15.1-bin.zip"
    
    echo "==> Installing Python..."
    wine msiexec /i python.msi
    
    cd _w/drive_c/windows
    ln -s ../Python27/python.exe .
    cd ../../..
    
    echo "==> Installing pywin32..."
    wine pywin32.exe
    
    echo "==> Installing PySide..."
    wine pyside.exe
    
    echo "==> Installing pip..."
    wine python get-pip.py
    
    echo "==> Installing six..."
    wine python -mpip install six
    
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
    unzip SDL.zip
    rm README-SDL.txt
    
    echo "==> Unpacking OpenAL..."
    unzip openal.zip
    mv openal-soft-*/Win32/soft_oal.dll openal.dll
    rm -r openal-soft-*
    
    echo "==> Cleaning up..."
    rm python.msi pywin32.exe pyside.exe get-pip.py pyinstaller.tar.gz 7z-inst.exe SDL.zip openal.zip
fi

echo "Building..."
git log | head -1 | cut -d " " -f 2 | cut -b -7 > ./commit

if [ -d PyInstaller-* ]; then
    wine python -OO PyInstaller-*/pyinstaller.py fs2mod-py.spec
else
    wine _w/drive_c/Python27/Scripts/pyinstaller fs2mod-py.spec
fi