#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager . src/releng/ubuntu/dist
rsync -a --exclude=releng --exclude=node_modules src/ work/

cd src
. releng/config/config.sh

if [ ! "$TRAVIS" = "y" ]; then
	if [ ! -d releng/ubuntu/cache ]; then
		sudo mkdir -p releng/ubuntu/cache
	fi
	sudo chown -R packager releng/ubuntu/cache

	cd releng/ubuntu/cache
	cp -a ../../../package.json .
	python3 ../../../tools/common/npm_wrapper.py
	if [ ! -d node_modules/es6-shim ]; then
		npm install es6-shim
	fi

	cd ../../..
fi
cd ../work

export QT_SELECT=5
if [ -z "$VERSION" ]; then
	VERSION="$(python3 setup.py get_version)"
fi
UBUNTU_VERSION="artful"

if [ "$TRAVIS" = "y" ]; then
	python tools/common/npm_wrapper.py
else
	rsync -au ../src/releng/ubuntu/cache/node_modules/ node_modules/
fi

python3 configure.py
ninja resources

tar -czf ../"knossos_$VERSION.orig.tar.gz" knossos setup.* DESCRIPTION.rst MANIFEST.in LICENSE NOTICE

mkdir ../knossos
cd ../knossos

tar -xzf ../"knossos_$VERSION.orig.tar.gz"
cp -a ../src/releng/ubuntu/debian .

if [ "$RELEASE" = "y" ]; then
	pushd /build/src > /dev/null
	import_key
	popd > /dev/null

	for ubuntu in $UBUNTU_VERSIONS; do
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
knossos ($VERSION-1) $UBUNTU_VERSION; urgency=medium

  * New upstream release

 -- ngld <ngld@tproxy.de>  Sun, 19 Feb 2017 16:23:14 +0100
EOF

	dpkg-buildpackage -us -uc

	cp ../knossos_*.deb /build/src/releng/ubuntu/dist
fi
