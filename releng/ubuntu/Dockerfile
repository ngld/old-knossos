FROM ubuntu:xenial

RUN apt-get update && apt-get upgrade -y && \
	apt-get install -y build-essential sudo gnupg debhelper pbuilder apt-file \
		python3-six python3-requests python3-semantic-version \
		python3-setuptools python3-pyqt5 python3-pyqt5.qtwebkit \
		pyqt5-dev-tools qtbase5-dev-tools libsdl2-2.0-0 libopenal1 p7zip-full \
		ninja-build rsync && \
	useradd -G sudo packager && \
	echo '%sudo ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

CMD ["/bin/bash"]
