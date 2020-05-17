#!/bin/bash

set -eo pipefail

cd "$(dirname "$0")"
rm -rf dist/*

vagrant rsync
vagrant ssh -- 'bash --login /opt/knossos/releng/macos/auto-build.sh'
vagrant ssh-config > /tmp/ssh_config
rsync -e 'ssh -F /tmp/ssh_config' -ar knossos-builder:/opt/knossos/releng/macos/dist .
rm /tmp/ssh_config
