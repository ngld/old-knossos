# A simple mod manager

The original idea and prototype were created by Hellzed.
ngld rewrote the manager in Python and extended it.

## Dependencies

To run this script you'll need the following:
* [Python][py] 2 or 3
* [PySide][pyside] or [PyQt4][pyqt]
* [Six][six]
* [semantic_version][sv]
* [requests][rq]
* [7zip][7z] (IMPORTANT: This script needs the full implementation, i.e. ```p7zip-full``` _and_ ```p7zip-rar``` on Ubuntu)
* [py-cpuinfo][cpuid] (included in third_party/)

The following commands should install everything you need:
* Ubuntu: ```apt-get install python3 python3-pyside.qtcore python3-pyside.qtgui python3-pyside.qtnetwork python3-pyside.qtwebkit python3-six python3-pip p7zip-full p7zip-rar && pip3 install semantic_version requests```
* Arch Linux: ```pacman -S python python-pyside python-six p7zip && pip install semantic_version requests```
  (You can replace the ```python-pyside``` package with the ```python-pyqt4``` package, if you want to.)

## Usage

To start the mod manager just run ```python -m knossos``` inside this directory.

The converter (which can load and convert the files from fsoinstaller.com) is a console-only script. Use ```python converter.py -h``` to read its help.

## Builds

A [Windows installer][win_inst] is available.
Other packages (Debian / Ubuntu, Arch Linux, ...) will be released soon.

## License

Licensed under the Apache License, Version 2.0.
See the [NOTICE](NOTICE) file for information.

The icon is borrowed from [Hard Light][hl].

[py]: http://www.python.org/
[pyside]: http://pyside.org/
[pyqt]: http://riverbankcomputing.co.uk/
[six]: https://pypi.python.org/pypi/six/
[7z]: http://www.7-zip.org/
[cpuid]: https://github.com/workhorsy/py-cpuinfo
[sv]: https://pypi.python.org/pypi/semantic_version
[rq]: https://pypi.python.org/pypi/requests
[pyi]: http://pyinstaller.org/

[hl]: http://www.hard-light.net/
[win_inst]: http://dev.tproxy.de/knossos/stable/installer.exe
