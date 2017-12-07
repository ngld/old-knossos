#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

. ../config/config.sh
exec docker build -t knossos-arch-builder .
