#!/bin/bash

set -eo pipefail

cd "$(dirname "$0")"
rm -rf dist/*

vagrant rsync
vagrant ssh -- 'cmd /C C:/knossos/releng/windows/auto-build.bat'
rsync -e 'ssh -F ssh_config' -ar knossos-builder:/cygdrive/c/knossos/releng/windows/dist .
