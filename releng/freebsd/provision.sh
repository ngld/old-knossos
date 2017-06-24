#!/bin/bash

pkg install -y ninja python27 py27-six py27-requests py27-semantic_version devel/py-qt5 qt5-buildtools p7zip sdl2 openal-soft npm
install -do vagrant /opt/knossos-prov
cd /opt/knossos-prov
sudo -u vagrant npm i babel-cli babel-preset-env
