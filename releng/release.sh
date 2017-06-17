#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

for fn in config/{config.sh,aur_key,signer.key}; do
	if ! [ -f "$fn" ]; then
		echo "ERROR: $fn is missing!"
		exit 1
	fi
done

. config/config.sh

if [ -z "$GPG_KEY_ID" ] || [ -z "$GITHUB_TOKEN" ]; then
	echo "ERROR: The config.sh file is missing either GPG_KEY_ID or GITHUB_TOKEN!"
	exit 1
fi

if ! which githubrelease > /dev/null 2>&1; then
	echo "githubrelease is missing!"
	exit 1
fi

echo "==> Preparing platforms..."
for plat in arch freebsd macos ubuntu windows; do
	"./$plat/prepare.sh"
done

VERSION="$(cd ..; python setup.py get_version | cut -d - -f -1)"
echo "==> Preparing release of $VERSION..."

git checkout master
git merge --no-commit -X theirs develop

sed -Ei "s#VERSION = '[^']+'#VERSION = '$VERSION'#" ../knossos/center.py

git commit -am "Release $VERSION"
git tag -u "$GPG_KEY_ID" "v$VERSION"


export RELEASE=y
echo "==> Building Windows..."
./windows/build.sh

echo "==> Building macOS..."
./macos/build.sh


echo "==> Pushing to GitHub..."
git push
git push --tags

echo "==> Building Ubuntu packages..."
./ubuntu/build.sh

echo "==> Building ArchLinux package..."
./arch/build.sh

echo "==> Building PyPi package..."
./pypi/build.sh

echo "==> Uploading artifacts to GitHub..."
githubrelease release ngld/knossos create "v$VERSION" --name "Knossos $VERSION" --publish windows/dist/{Knossos,update}-"$VERSION".exe macos/dist/Knossos-"$VERSION".dmg

echo "==> Killing VMs..."
cd windows
vagrant destroy

cd ../macos
vagrant destroy

echo "==> Done."
