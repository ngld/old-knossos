#!/bin/bash

set -eo pipefail

if [ "$TRAVIS_OS_NAME" == "osx" ] && [ -n "$TRAVIS_TAG" ]; then
    . releng/config/config.sh

    export PATH="/Library/Frameworks/Python.framework/Versions/3.6/bin:$PATH"

    echo "==> Installing githubrelease"
    pip3 install githubrelease

    echo "==> Uploading build"
    githubrelease asset ngld/knossos upload "$TRAVIS_TAG" releng/macos/dist/*.dmg
fi
