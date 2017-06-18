FROM mailsvb/arch-linux:latest

ADD aur.sh /usr/bin/aur

RUN pacman -Syu --needed --noconfirm base-devel sudo python pkgbuild-introspection \
		python-six python-requests python-pyqt5 python-raven qt5-webengine \
		qt5-webchannel qt5-tools sdl2 openal p7zip ninja rsync && \
	chmod a+x /usr/bin/aur && \
	useradd -mG wheel packager && \
	echo '%wheel ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers && \
	install -do packager /scratch && \
	sudo -u packager aur -sci --noconfirm --noprogress python-semantic-version && \
	rm -r /scratch/*

CMD ["/bin/bash"]
