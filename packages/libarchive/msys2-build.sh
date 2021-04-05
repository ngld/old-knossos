#!/bin/sh

set -e

cd "$(dirname "$0")"/../..
mkdir -p build/libarchive
cd build/libarchive

export PATH="/mingw64/bin:$PATH"

if [ ! -f CMakeCache.txt ]; then
    cmake -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -Wno-dev \
        -DENABLE_ACL=OFF \
        -DENABLE_BZip2=OFF \
        -DENABLE_CNG=OFF \
        -DENABLE_CPIO=OFF \
        -DENABLE_EXPAT=OFF \
        -DENABLE_LIBXML2=OFF \
        -DENABLE_LZ4=OFF \
        -DENABLE_OPENSSL=OFF \
        -DENABLE_PCREPOSIX=OFF \
        -DENABLE_TAR=OFF \
        -DENABLE_TEST=OFF \
        -DENABLE_CAT=OFF \
        ../../third_party/libarchive
fi

make -j4 archive_static
