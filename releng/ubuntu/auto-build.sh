#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager .
rsync -a --exclude=releng src/ work/

cd src
. releng/config/config.sh
import_key

cd ../work

export QT_SELECT=5
VERSION="$(python3 setup.py get_version)"
UBUNTU_VERSION="xenial"

python3 configure.py
ninja resources

tar -czf ../"knossos_$VERSION.orig.tar.gz" knossos setup.* DESCRIPTION.rst MANIFEST.in LICENSE NOTICE

mkdir ../knossos
cd ../knossos

tar -xzf ../"knossos_$VERSION.orig.tar.gz"
cp -a ../src/releng/ubuntu/debian .

if [ "$RELEASE" = "y" ]; then
	gpg-agent --daemon

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
