#!/bin/bash

pkg install -y ninja python27 py27-pip py27-six py27-requests py27-semantic_version devel/py-qt5 qt5-buildtools p7zip sdl2 openal-soft
python2.7 -mpip install ninja-syntax
