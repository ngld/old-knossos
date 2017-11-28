#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager .
rsync -a --exclude=releng --exclude=node_modules src/ work/
cd src

. releng/config/config.sh
import_key

cd ../work

export QT_SELECT=5
VERSION="$(python3 setup.py get_version)"

if [ -d dist ]; then
	rm -rf dist/*
fi

npm install
npm install es6-shim

python3 configure.py
ninja dist

echo "Signing..."
for file in dist/*; do
	gpg -au "$GPG_KEY_ID" --detach-sign "$file"
done

echo "Uploading..."
twine upload dist/*
