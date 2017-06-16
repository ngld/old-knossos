#!/bin/bash

set -eo pipefail

cd /build
sudo chown packager .
rsync -a --exclude=dist --exclude=build --exclude=packer --exclude=.vagrant src/ work/
cd work

export QT_SELECT=5
VERSION="$(python3 setup.py get_version)"
UBUNTU_VERSION="xenial"

echo "Installing Babel..."
rm -rf node_modules
npm i babel-cli babel-preset-env

python3 configure.py
ninja resources

tar -czf ../"knossos_$VERSION.orig.tar.gz" knossos html setup.* DESCRIPTION.rst MANIFEST.in LICENSE NOTICE

mkdir ../knossos
cd ../knossos

tar -xzf ../"knossos_$VERSION.orig.tar.gz"
cp -a ../src/releng/ubuntu/debian .

cat > debian/changelog <<EOF
knossos ($VERSION-1) $UBUNTU_VERSION; urgency=medium

  * New upstream release

 -- ngld <ngld@tproxy.de>  Sun, 19 Feb 2017 16:23:14 +0100
EOF

dpkg-buildpackage -us -uc
# dpkg-buildpackage -S -sa -k<key>
# dput ???

cp ../knossos_*.deb /build/src/releng/ubuntu/dist
