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
    download get-pip.py "https://raw.github.com/pypa/pip/master/contrib/get-pip.py"
    download pyinstaller.tar.gz "https://pypi.python.org/packages/source/P/PyInstaller/PyInstaller-2.1.tar.gz"
    download upx.zip "http://upx.sourceforge.net/download/upx391w.zip"
    download 7z-inst.exe "http://downloads.sourceforge.net/sevenzip/7z920.exe"
    download qt.exe "http://download.qt-project.org/official_releases/qt/4.8/4.8.5/qt-win-opensource-4.8.5-vs2008.exe"
    
    echo "==> Installing Python..."
    wine msiexec /i python.msi
    
    pushd _w/drive_c/windows > /dev/null
    ln -s ../Python27/python.exe .
    popd > /dev/null
    
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
    
    echo "==> Unpacking Qt..."
    mkdir tmp
    7z x -otmp qt.exe
    mv 'tmp/$OUTDIR/bin/lib/'Qt{Gui,Core}4.dll .
    rm -r tmp
    
    echo "==> Cleaning up..."
    rm python.msi pywin32.exe pyside.exe get-pip.py pyinstaller.tar.gz 7z-inst.exe qt.exe
fi

echo "Building..."
git log | head -1 | cut -d " " -f 2 | cut -b -7 > ./commit

if [ -d PyInstaller-* ]; then
    wine python PyInstaller-*/pyinstaller.py fs2mod-py.spec
else
    wine _w/drive_c/Python27/Scripts/pyinstaller fs2mod-py.spec
fi