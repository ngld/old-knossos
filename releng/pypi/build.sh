#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

if [ "$RELEASE" = "y" ]; then
	exec docker run --rm -it -v"$(cd ../..; pwd)":/build/src -u packager knossos-ubuntu-builder bash /build/src/releng/pypi/auto-build.sh
fi
