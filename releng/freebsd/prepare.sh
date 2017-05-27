#!/bin/bash

set -eo pipefail

cd "$(dirname "$0")"
if [ ! -d packer ]; then
	git clone --depth=1 https://github.com/jlduran/packer-FreeBSD packer
fi

if [ ! -f packer/builds/FreeBSD-11.0-RELEASE-amd64.box ]; then
	cd packer
	packer build -var-file=variables.json template.json
	cd ..
fi

vagrant up
vagrant ssh-config > ssh_config
