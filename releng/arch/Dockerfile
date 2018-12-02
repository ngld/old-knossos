FROM mailsvb/arch-linux:latest

ADD aur.sh /usr/bin/aur

RUN pacman -Sy --noconfirm archlinux-keyring && \
	pacman -Su --needed --noconfirm base-devel sudo python \
		python-six python-requests python-requests-toolbelt python-ply python-pyqt5 python-raven \
		qt5-webengine qt5-webchannel qt5-tools sdl2 openal p7zip ninja rsync git openssh nodejs yarn && \
	chmod a+x /usr/bin/aur && \
	useradd -mG wheel packager && \
	echo '%wheel ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers && \
	install -do packager /scratch && \
	sudo -u packager aur -sci --noconfirm --noprogress python-semantic-version python-token-bucket && \
	rm -r /scratch/*

CMD ["/bin/bash"]
