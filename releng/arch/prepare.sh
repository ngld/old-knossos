#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

. ../config/config.sh
exec docker build -t knossos-arch-builder --build-arg AUR_USER="$AUR_USER" --build-arg AUR_EMAIL="$AUR_EMAIL" .
