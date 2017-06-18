#!/bin/bash

if [ ! -d /scratch ]; then
	mkdir /scratch
fi

for p in ${@##-*}; do
	cd /scratch
	curl "https://aur.archlinux.org/cgit/aur.git/snapshot/$p.tar.gz" | tar xz
	cd "$p"
	makepkg ${@##[^\-]*}
done
