#!/bin/bash

mypath="$(cd "$(dirname "$0")" ; pwd)"
set -e

has() {
    which "$@" > /dev/null 2>&1
}

mingw-get install msys-make
mingw-get install msys-wget
mingw-get install msys-liblzma
mingw-get install mingw32-libiconv
mingw-get install msys-bzip2
mingw-get install msys-zlib
mingw-get install msys-unzip
mingw-get install msys-patch

echo "Fix a dumb bug in MinGW's headers..."

sed -i 's# off_t# _off_t#g' /mingw/include/*.h
sed -i 's# off64_t# _off64_t#g' /mingw/include/*.h

cd /
if ! has cmake; then
    echo "Installing cmake..."

    wget -O cmake.zip "http://www.cmake.org/files/v2.8/cmake-2.8.12.2-win32-x86.zip"
    unzip cmake.zip
    mv cmake-*/bin/* bin
    mv cmake-*/share/* share

    rm -r cmake.zip cmake-*
fi

[ -d /build ] && rm -r /build
mkdir /build
cd /build

echo "Downloading zlib..."
wget "http://zlib.net/zlib-1.2.8.tar.xz"

tar -xJf zlib-*.tar.xz
rm zlib-*.tar.xz
export ZLIB_SOURCE="$(echo "$PWD/"zlib-*)"

cd "$ZLIB_SOURCE"
make -f win32/Makefile.gcc
cd ..

echo "Downloading bzip2..."
wget "http://www.bzip.org/1.0.6/bzip2-1.0.6.tar.gz"

tar -xzf bzip2-*.tar.gz
rm bzip2-*.tar.gz
export BZIP2_SOURCE="$(echo "$PWD/"bzip2-*)"

cd "$BZIP2_SOURCE"
make
cd ..

echo "Downloading boost..."
wget -O boost.tar.bz2 "http://sourceforge.net/projects/boost/files/boost/1.55.0/boost_1_55_0.tar.bz2/download"

echo "Unpacking boost..."
echo "NOTE: The archive is *really* big, this could take some time."
tar -xjf boost.tar.bz2
rm boost.tar.bz2

echo "Compiling bjam..."
cd boost_*
# Build bjam first...
sh ./bootstrap.sh --with-toolset=mingw

echo "Configuring boost..."
# Now do the actual bootstrap.
sh ./bootstrap.sh --with-bjam=bjam.exe

echo "Compiling boost..."
# Now on to compiling...
./b2 -j4 --with-iostreams --with-filesystem --with-system --with-program_options --with-date_time

cd ..

echo "Building innoextract..."
wget "http://constexpr.org/innoextract/files/innoextract-1.4.tar.gz"
tar -xzf innoextract-*.tar.gz
rm innoextract-*.tar.gz

cd innoextract-*
# TODO: Change
# wget "https://github.com/ngld/fs2mod-py/raw/master/innoextract-1.4.patch"
patch -p1 < "$(echo "$mypath"/innoextract-*.patch)"

mkdir build
cd build
cmake -G"MSYS Makefiles" .. -DLZMA_INCLUDE_DIR=/include -Diconv_INCLUDE_DIR=/mingw/include \
    -DBOOST_INCLUDEDIR="$(echo /build/boost_*/)" -DZLIB_INCLUDE_DIR="$(echo /build/zlib-*/)" \
    -DBZIP2_INCLUDE_DIR="$(echo /build/bzip2-*/)" -DBZIP2_LIBRARIES="$(echo /build/bzip2-*/*.a)"
make
