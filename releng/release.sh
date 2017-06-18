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

if [ -n "$1" ]; then
	VERSION="$1"
fi

echo "==> Preparing platforms..."
for plat in arch freebsd macos ubuntu windows; do
	"./$plat/prepare.sh"
done

if [ "$(cat ../.git/HEAD)" = "ref: refs/heads/develop" ]; then
	if [ -z "$VERSION" ]; then
		VERSION="$(cd ..; python setup.py get_version | cut -d - -f -1)"
	fi
	echo "==> Preparing release of $VERSION..."

	git checkout master
	git merge --no-commit -X theirs develop

	sed -Ei "s#VERSION = '[^']+'#VERSION = '$VERSION'#" ../knossos/center.py
else
	if [ -z "$VERSION" ]; then
		VERSION="$(cd ..; python setup.py get_version)"
	fi
fi

rel_text="$(mktemp)"
cat > "$rel_text" <<EOF


# Please enter your release notes above.
# All lines starting with an # are ignored.
EOF
"$EDITOR" "$rel_text"

grep -v '^#' "$rel_text" > "$rel_text.stripped"
mv "$rel_text.stripped" "$rel_text"

git commit -am "Release $VERSION"
git tag -u "$GPG_KEY_ID" -m "$(cat "$rel_text")" "v$VERSION"

cat >> "$rel_text" <<EOF

[PPA](https://launchpad.net/~ngld/+archive/ubuntu/knossos) | [AUR](https://aur.archlinux.org/packages/fs2-knossos/) | [PyPI](https://pypi.python.org/pypi/knossos)
EOF

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
githubrelease release ngld/knossos create "v$VERSION" --name "Knossos $VERSION" --body "$(cat "$rel_text")" \
	--publish --prerelease \
	windows/dist/{Knossos,update}-"$VERSION".exe macos/dist/Knossos-"$VERSION".dmg

rm "$rel_text"

echo "==> Killing VMs..."
cd windows
vagrant destroy

cd ../macos
vagrant destroy

echo "==> Done."
