#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

# You might need to run "xhost +local:docker" to allow access to your X.org server from inside the container.

exec docker run --rm -it --privileged -v/tmp/.X11-unix:/tmp/.X11-unix -v"$(cd ../..; pwd)":/build/src \
	-u packager -e DISPLAY="$DISPLAY" knossos-ubuntu-builder bash /build/src/releng/ubuntu/auto-run.sh
