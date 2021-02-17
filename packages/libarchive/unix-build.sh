#!/bin/bash

set -eo pipefail

cd ../../build
if [ ! -d libarchive ]; then
	mkdir libarchive
fi
cd libarchive

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
	../../third_party/libarchive

make -j4 archive
