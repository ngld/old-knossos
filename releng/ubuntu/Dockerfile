FROM ubuntu:xenial

RUN apt-get update && apt-get upgrade -y && \
	apt-get install -y build-essential sudo gnupg debhelper pbuilder apt-file \
		python3-six python3-requests python3-semantic-version \
		python3-setuptools python3-pyqt5 python3-pyqt5.qtwebkit \
		pyqt5-dev-tools qtbase5-dev-tools libsdl2-2.0-0 libopenal1 p7zip-full \
		ninja-build rsync npm twine python3-wheel gnupg-agent gnupg2 pinentry-tty gdb && \
	useradd -mG sudo packager && \
	echo '%sudo ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers && \
	install -do packager /build && \
	ln -s nodejs /usr/bin/node

CMD ["/bin/bash"]
