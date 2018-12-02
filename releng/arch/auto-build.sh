#!/bin/bash

set -eo pipefail

sudo chown packager .

if [ -d work ]; then
	rm -rf work
fi

if [ -z "$CI" ]; then
	# Make a "clean" copy of the source dir (without the files in .gitignore) to avoid
	# modifying a local checkout mounted via -v

	git clone . work

	cd src
	git diff > ./work/pp
	cd ./work

	if [ -n "$(cat pp)" ]; then
		git apply pp
	fi

	rm pp
else
	ln -s . work
	cd work
fi

if [ "$RELEASE" = "y" ]; then
	. releng/config/config.sh

	if [ "$DRONE" = "true" ]; then
		echo "$AUR_SSH_KEY" > releng/config/aur_key
	fi

	install -Dm600 releng/config/aur_key ~/.ssh/id_ecdsa

	# Disable interactive question for unknown host keys
	echo -e "Host aur.archlinux.org\n\tIdentityFile ~/.ssh/id_ecdsa\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile=/dev/null\n" > ~/.ssh/config

	git config --global user.name "$AUR_USER"
	git config --global user.email "$AUR_EMAIL"

	if [ -z "$VERSION" ]; then
		VERSION="$(python setup.py get_version | cut -d - -f 1)"
	fi

	cd releng/arch
	if [ -d pkg ]; then
		rm -rf pkg
	fi

	git clone aur@aur.archlinux.org:fs2-knossos.git pkg
	cd pkg

	sed -e 's#^pkgver=.*#pkgver='"$VERSION"'#' -e 's#^pkrel=.*#pkgrel=1#' < ../PKGBUILD > PKGBUILD
	updpkgsums
	makepkg --srcinfo > .SRCINFO

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
