#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

exec docker run --rm -it -v"$(cd ../..; pwd)":/build/src -u packager -e RELEASE="${RELEASE:-n}" -e VERSION="$VERSION" knossos-ubuntu-builder bash /build/src/releng/ubuntu/auto-build.sh
