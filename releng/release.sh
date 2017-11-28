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

echo "==> Stashing local changes to protect them"
git stash

echo "==> Preparing platforms..."
for plat in arch macos ubuntu windows; do
	"./$plat/prepare.sh"
done

switched=no
if [ "$(cat ../.git/HEAD)" = "ref: refs/heads/develop" ]; then
	if [ -z "$VERSION" ]; then
		VERSION="$(cd ..; python setup.py get_version | cut -d - -f -1)"
	fi
	echo "==> Preparing release of $VERSION..."

	git checkout master
	git merge --no-commit -X theirs develop
	switched=yes

	sed -Ei "s#VERSION = '[^']+'#VERSION = '$VERSION'#" ../knossos/center.py
	git add ../knossos/center.py
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

git commit -m "Release $VERSION"
git tag -u "$GPG_KEY_ID" -m "$(cat "$rel_text")" "v$VERSION"

cat >> "$rel_text" <<EOF

[PPA](https://launchpad.net/~ngld/+archive/ubuntu/knossos) | [AUR](https://aur.archlinux.org/packages/fs2-knossos/) | [PyPI](https://pypi.python.org/pypi/knossos)
EOF

export RELEASE=y
error=no
failed=()

echo "==> Building Windows..."
if ! ./windows/build.sh; then
	error=yes
	failed+=(Windows)
fi

echo "==> Building macOS..."
if ! ./macos/build.sh; then
	error=yes
	failed+=(macOS)
fi

if [ "$error" = "yes" ]; then
	echo "!!> Aborting build since one or more platforms failed!"

	if [ "$switched" = "yes" ]; then
		git reset --hard origin/master
		git tag -d "v$VERSION"
		git checkout develop
	fi

	echo "${failed[@]} failed"
	exit 1
fi

# Point of no return

echo "==> Pushing to GitHub..."
git push
git push --tags

echo "==> Building Ubuntu packages..."
if ! ./ubuntu/build.sh; then
	failed+=(Ubuntu)
fi

echo "==> Building ArchLinux package..."
if ! ./arch/build.sh; then
	failed+=(Arch)
fi

echo "==> Building PyPi package..."
if ! ./pypi/build.sh; then
	failed+=(PyPI)
fi

echo "==> Uploading artifacts to GitHub..."
githubrelease release ngld/knossos create "v$VERSION" --name "Knossos $VERSION" --publish --prerelease \
	windows/dist/{Knossos,update}-"$VERSION".exe macos/dist/Knossos-"$VERSION".dmg

githubrelease release ngld/knossos edit "v$VERSION" --body "$(cat "$rel_text")" 

echo "==> Announcing update..."
curl "https://dev.tproxy.de/knossos/stable/update_version.php"
echo ""

if [ "${#failed[@]}" -gt 0 ]; then
	echo "WARNING: ${failed[@]} failed!"
fi

rm "$rel_text"


if [ "$switched" = "yes" ]; then
	git checkout develop
fi

echo "==> Done."
