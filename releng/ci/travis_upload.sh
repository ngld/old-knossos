#!/bin/bash

set -exo pipefail

if [ "$TRAVIS_OS_NAME" == "osx" ] && [ -n "$TRAVIS_TAG" ]; then
    . releng/config/config.sh

    echo "==> Installing githubrelease"
    pip3 install githubrelease

    echo "==> Uploading build"
    githubrelease asset ngld/knossos upload "$TRAVIS_TAG" releng/macos/dist/*.dmg
fi
