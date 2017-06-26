#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

exec docker run --rm -it --privileged -v/tmp/.X11-unix:/tmp/.X11-unix -v"$(cd ../..; pwd)":/build/src \
	-u packager -e DISPLAY="$DISPLAY" knossos-ubuntu-builder bash /build/src/releng/ubuntu/auto-run.sh
