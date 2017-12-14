FROM ubuntu:artful

RUN apt-get update && apt-get upgrade -y && \
	apt-get install -y build-essential sudo gnupg debhelper pbuilder apt-file \
		python3-six python3-requests python3-requests-toolbelt python3-ply \
		python3-semantic-version python3-setuptools python3-pyqt5 python3-pyqt5.qtwebengine \
		python3-pyqt5.qtwebchannel pyqt5-dev-tools qtbase5-dev-tools libsdl2-2.0-0 libopenal1 \
		p7zip-full ninja-build rsync npm twine python3-wheel gnupg-agent gnupg2 pinentry-tty gdb \
		python-software-properties software-properties-common && \
	add-apt-repository ppa:ngld/knossos && \
	apt-get update && \
	apt-get install -y python3-token-bucket

RUN useradd -mG sudo packager && \
	echo '%sudo ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers && \
	install -do packager /build

CMD ["/bin/bash"]
