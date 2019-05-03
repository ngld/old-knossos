#!/bin/bash

set -eo pipefail

sudo chown packager . releng/ubuntu/dist

if [ -d work ]; then
	rm -r work
fi

if [ -z "$CI" ]; then
	# Make a "clean" copy of the source dir (without the files in .gitignore) to avoid
	# modifying a local checkout mounted via -v

	git clone . work
	git diff > ./work/pp
	
	cd ./work
	if [ -n "$(cat pp)" ]; then
		git apply pp
	fi
	rm pp
	cd ..
fi

if [ "$DRONE" = "true" ]; then
	if [ -n "$UBUNTU_GPG_KEY" ]; then
		echo "$UBUNTU_GPG_KEY" | gpg --import /dev/stdin
	fi
else
	. releng/config/config.sh
	import_key
fi

if [ -z "$CI" ]; then
	cd work
fi

export QT_SELECT=5
if [ -z "$VERSION" ]; then
	VERSION="$(python3 setup.py get_version)"
fi

python3 tools/common/npm_wrapper.py
python3 configure.py
ninja resources

tar -czf "knossos_$VERSION.orig.tar.gz" knossos setup.* DESCRIPTION.rst MANIFEST.in LICENSE NOTICE

mkdir deb_work
cd deb_work

tar -xzf ../"knossos_$VERSION.orig.tar.gz"
cp -a ../releng/ubuntu/debian .

if [ "$RELEASE" = "y" ]; then
	for ubuntu in bionic cosmic; do
		cat > debian/changelog <<EOF
knossos ($VERSION-1~${ubuntu}1) $ubuntu; urgency=medium

  * New upstream release

 -- ngld <ngld@tproxy.de>  Sun, 19 Feb 2017 16:23:14 +0100
EOF

		dpkg-buildpackage -S -sa -k$UBUNTU_KEY
	done

	dput ppa:ngld/knossos ../knossos_$VERSION-1~*.changes
else
	cat > debian/changelog <<EOF
knossos ($VERSION-1) cosmic; urgency=medium

  * New upstream release

 -- ngld <ngld@tproxy.de>  Sun, 19 Feb 2017 16:23:14 +0100
EOF

	dpkg-buildpackage -us -uc

	cp ../knossos_*.deb ../releng/ubuntu/dist
fi
