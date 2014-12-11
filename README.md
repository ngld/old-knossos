# A simple mod manager

The original idea and prototype were created by Hellzed.
ngld rewrote the manager in Python and extended it.

## Website

There's a small website with installation instructions at https://dev.tproxy.de/knossos/.

## Dependencies

To run this script you'll need the following:
* [Python][py] 2 or 3
* [Qt 4][qt]
* [PySide][pyside] or [PyQt4][pyqt]
* [Six][six]
* [semantic_version][sv]
* [requests][rq]
* If you're using Python2 you will also need [ndg-httpsclient][nhs] and [pyasn1][pan]
* [7zip][7z] (IMPORTANT: This script needs the full implementation, i.e. ```p7zip-full``` _and_ ```p7zip-rar``` on Ubuntu)
* [py-cpuinfo][cpuid] (included in third_party/)

## Usage

To start the mod manager just run ```make run``` inside this directory.
If it complains that ```pyside-uic``` or ```rcc``` is missing, you need to install the developer packages for PySide and Qt4.

The converter is a console-only script. Use ```python converter.py -h``` to read its help.

## License

Licensed under the Apache License, Version 2.0.
See the [NOTICE](NOTICE) file for information.

The icon is borrowed from [Hard Light][hl].

[py]: http://www.python.org/
[qt]: http://www.qt.io/
[pyside]: http://pyside.org/
[pyqt]: http://riverbankcomputing.co.uk/
[six]: https://pypi.python.org/pypi/six/
[7z]: http://www.7-zip.org/
[cpuid]: https://github.com/workhorsy/py-cpuinfo
[sv]: https://pypi.python.org/pypi/semantic_version
[rq]: https://pypi.python.org/pypi/requests
[nhs]: https://pypi.python.org/pypi/ndg-httpsclient
[pan]: https://pypi.python.org/pypi/pyasn1
[pyi]: http://pyinstaller.org/

[hl]: http://www.hard-light.net/
[win_inst]: http://dev.tproxy.de/knossos/stable/installer.exe
