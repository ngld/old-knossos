#!/bin/bash

set -eo pipefail
base=/opt/knossos

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "${DIR}"

source ./functions.sh

install_clitools

install_nvm

install_yarn

install_homebrew

install_brews

mkdir /tmp/prov
cd /tmp/prov

install_SDL2

install_qt5

install_python

echo "==> Cleanup"
cd "${base}"
rm -r /tmp/prov

install_pideps
