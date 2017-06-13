#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

exec docker run -v"$(cd ../..; pwd)":/build/src -u packager knossos-ubuntu-builder bash /build/src/releng/ubuntu/auto-build.sh
