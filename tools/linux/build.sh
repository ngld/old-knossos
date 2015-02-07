#!/bin/bash
## Copyright 2015 Knossos authors, see NOTICE file
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

set -e

cd "$(dirname "$0")"
PLATFORM=linux
. ../common/helpers.sh
init_build_script "$@"

if ! has tar || ! has git; then
    error "Sorry, but I need tar and git to generate a linux build."
    exit 1
fi

msg "Building..."
generate_version > version

pushd ../..
make ui resources
popd

msg2 "Building package..."
[ -d dist ] && rm -rf dist
mkdir dist

dist_path="$(pwd)/dist"
pushd ../..
python setup.py install --optimize 2 --root "$dist_path" --install-lib .
popd

mv version dist/knossos

if [ "$gen_package" = "y" ]; then
    msg2 "Compressing..."

    cd dist
    tar -czf knossos.tar.gz knossos
    rm -r knossos{,*egg-info*} usr
fi
