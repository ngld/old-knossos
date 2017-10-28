#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

exec docker run --rm -it -v"$(cd ../..; pwd)":/build/src -u packager -e RELEASE="${RELEASE:-n}" knossos-arch-builder bash /build/src/releng/arch/auto-build.sh
