FROM mailsvb/arch-linux:latest

ARG AUR_USER
ARG AUR_EMAIL

ADD aur.sh /usr/bin/aur

RUN pacman -Sy --noconfirm archlinux-keyring && \
	pacman -Su --needed --noconfirm base-devel sudo python pkgbuild-introspection \
		python-six python-requests python-requests-toolbelt python-ply python-pyqt5 python-raven \
		qt5-webengine qt5-webchannel qt5-tools sdl2 openal p7zip ninja rsync git openssh nodejs npm && \
	chmod a+x /usr/bin/aur && \
	useradd -mG wheel packager && \
	echo '%wheel ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers && \
	install -do packager /scratch && \
	sudo -u packager aur -sci --noconfirm --noprogress python-semantic-version && \
	rm -r /scratch/* && \
	sudo -u packager git config --global user.name "$AUR_USER" && \
	sudo -u packager git config --global user.email "$AUR_EMAIL"

CMD ["/bin/bash"]
