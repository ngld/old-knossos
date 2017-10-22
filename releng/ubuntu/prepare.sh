#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

exec docker build -t knossos-ubuntu-builder .
