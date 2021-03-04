#!/bin/bash

set -eo pipefail

cd "$(dirname "$0")"

if !which go > /dev/null 2>&1; then
	echo "Please install the Golang toolchain and run this script again."
	exit 1
fi

if [ ! -f .tools/tool ]; then
    cd packages/build-tools
    echo "Building build-tools"
    go build -o ../../.tools/tool
    cd ../..
fi

exec ./.tools/tool task "$@"
