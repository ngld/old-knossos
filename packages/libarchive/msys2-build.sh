#!/bin/sh

set -e

cd "$(dirname "$0")"/../..
mkdir -p build/libarchive
cd build/libarchive

export PATH="/mingw64/bin:$PATH"

if [ ! -f CMakeCache.txt ]; then
    args=(
        -DCMAKE_BUILD_TYPE=Release
        -Wno-dev
        # Enable only necessary features
        -DENABLE_ACL=OFF
        -DENABLE_BZip2=OFF
        -DENABLE_CNG=OFF
        -DENABLE_CPIO=OFF
        -DENABLE_EXPAT=OFF
        -DENABLE_LIBXML2=OFF
        -DENABLE_LZ4=OFF
        -DENABLE_OPENSSL=OFF
        -DENABLE_PCREPOSIX=OFF
        -DENABLE_TAR=OFF
        -DENABLE_TEST=OFF
        -DENABLE_CAT=OFF
        # Force CMake to link against static libraries
        -DLIBICONV_PATH=/mingw64/lib/libiconv.a
        -DLIBCHARSET_PATH=/mingw64/lib/libcharset.a
        -DREGEX_LIBRARY=/mingw64/lib/libregex.a
        -DZLIB_LIBRARY=/mingw64/lib/libz.a
        -DLIBLZMA_LIBRARY=/mingw64/lib/liblzma.a
        -DZSTD_LIBRARY=/mingw64/lib/libzstd.a

        ../../third_party/libarchive
    )

    cmake -G"Unix Makefiles" "${args[@]}"
fi

make -j4 archive_static
