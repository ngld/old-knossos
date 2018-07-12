#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager . src/releng/ubuntu/dist

if [ -d work ]; then
	cd work
	git reset --hard
	git pull
	cd ..
else
	git clone src work
fi

cd src
git diff > ../work/pp
cd ../work
git apply pp
rm pp

cd src
. releng/config/config.sh
cd ../work

export QT_SELECT=5
if [ -z "$VERSION" ]; then
	VERSION="$(python3 setup.py get_version)"
fi
UBUNTU_VERSION="artful"

python3 tools/common/npm_wrapper.py
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

	for ubuntu in artful bionic cosmic; do
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
