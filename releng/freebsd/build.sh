#!/bin/bash

set -eo pipefail

cd "$(dirname "$0")"
vagrant rsync
vagrant ssh -- 'sh /opt/knossos/releng/freebsd/auto-build.sh'
rsync -e 'ssh -F ssh_config' -ar knossos-builder:/opt/knossos/releng/freebsd/dist .
