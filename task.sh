#!/bin/sh

set -e

cd "$(dirname "$0")"

if ! command -v go > /dev/null 2>&1; then
    echo "Please install the Golang toolchain and run this script again."
    exit 1
fi

if [ ! -f .tools/tool ]; then
    (
        cd packages/build-tools
        echo "Building build-tools..."
        go build -o ../../.tools/tool
    )
fi

exec ./.tools/tool task "$@"
