#!/bin/bash

set -eo pipefail

cd "$(dirname "$0")"
rm -rf dist/*

vagrant rsync
vagrant ssh -- 'bash /opt/knossos/releng/macos/auto-build.sh'
rsync -e 'ssh -F ssh_config' -ar knossos-builder:/opt/knossos/releng/macos/dist .
