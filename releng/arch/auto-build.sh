#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager .
rsync -au --exclude=dist --exclude=build --exclude=packer --exclude=.vagrant --exclude=node_modules src/ work/
cd work

if [ "$RELEASE" = "y" ]; then
	. releng/config/config.sh

	install -Dm600 releng/config/aur_key ~/.ssh/id_rsa
	echo "StrictHostKeyChecking no" > ~/.ssh/ssh_config

	git config --global user.name "$AUR_USER"
	git config --global user.email "$AUR_EMAIL"

	VERSION="$(python setup.py get_version | cut -d - -f 1)"

	cd releng/arch
	if [ -d pkg ]; then
		rm -rf pkg
	fi

	git clone aur@aur.archlinux.org:fs2-knossos.git pkg
	cd pkg

	sed -e 's#^pkgver=.*#pkgver='"$VERSION"'#' -e 's#^pkrel=.*#pkgrel=1#' < ../PKGBUILD > PKGBUILD
	updpkgsums
	mksrcinfo

	# Make sure we can actually build the package
	makepkg -c

	git add .SRCINFO PKGBUILD
	git commit -m 'New upstream release'
	git push
else
	python tools/common/npm_wrapper.py
	python configure.py
	ninja resources
fi
