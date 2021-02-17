#!/bin/bash

set -eo pipefail

cd ../../build
if [ ! -d libarchive ]; then
	mkdir libarchive
fi
cd libarchive

export PATH="/mingw64/bin:$PATH"

pacman -S --noconfirm --noreinstall mingw-w64-x86_64-{gcc,xz,cmake} make

cmake -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -Wno-dev \
	-DENABLE_ACL=OFF \
	-DENABLE_BZip2=OFF \
	-DENABLE_CNG=OFF \
	-DENABLE_CPIO=OFF \
	-DENABLE_EXPAT=OFF \
	-DEANBLE_LIBXML2=OFF \
	-DENABLE_LZ4=OFF \
	-DENABLE_OPENSSL=OFF \
	-DENABLE_PCREPOSIX=OFF \
	-DENABLE_TAR=OFF \
	-DENABLE_TEST=OFF \
	-DENABLE_CAT=OFF \
	-DLIBICONV_PATH=/mingw64/lib/libiconv.a \
	-DLIBCHARSET_PATH=/mingw64/lib/libcharset.a \
    -DREGEX_LIBRARY=/mingw64/lib/libregex.a \
	-DZLIB_LIBRARY=/mingw64/lib/libz.a \
	-DLIBLZMA_LIBRARY=/mingw64/lib/liblzma.a \
    -DZSTD_LIBRARY=/mingw64/lib/libzstd.a \
	../../third_party/libarchive

make -j4 archive
