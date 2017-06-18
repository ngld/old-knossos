#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager .
rsync -a --exclude=dist --exclude=build --exclude=packer --exclude=.vagrant src/ work/
cd work

install -Dm600 releng/config/aur_key ~/.ssh/id_rsa

if [ "$RELEASE" = "y" ]; then
	VERSION="$(python setup.py get_version | cut -d - -f 1)"

	cd releng/arch/pkg
	sed -i 's#^pkgver=.*#pkgver='"$VERSION"'#g' PKGBUILD
	updpkgsums
	mksrcinfo

	# Make sure we can actually build the package
	makepkg -c

	git add .SRCINFO PKGBUILD
	git commit -m 'New upstream release'
	git push
else
	python configure.py
	ninja resources
fi
