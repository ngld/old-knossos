# A simple mod manager

The original idea and prototype were created by Hellzed.
ngld rewrote the manager in Python and extended it.

## Website

[**Installation instructions**](https://dev.tproxy.de/knossos/)

## Dependencies

To run this script you'll need the following:
* [Python][py] 2 or 3
* [Qt 5][qt]
* [PyQt5][pyqt]
* [Six][six]
* [semantic_version][sv]
* [requests][rq]
* If you're using Python 2 < 2.8 you will also need [ndg-httpsclient][nhs] and [pyasn1][pan]
* [7zip][7z] (IMPORTANT: This script needs the full implementation, i.e. ```p7zip-full``` _and_ ```p7zip-rar``` on Ubuntu)
* [raven][rv] (optional, neccessary to automatically report errors)

[py-cpuinfo][cpuid] is included in third_party/.

## Usage

After your first checkout you will have to run `python configure.py` once. If it aborts before displaying `Writing build.ninja...`, you have to fix the error before you can continue.
If it complains that ```rcc``` is missing, you will need to install the developer packages for Qt5.

Now you can use `ninja run` to launch Knossos in release mode and `ninja debug` to launch it in debug mode. In debug mode you can use a chromium-based browser to access the DevTools by navigating to http://localhost:4006/.

If you delete or add files in `html/images` or `html/templates` you have to run
`configure.py` again because it needs to rebuild the file list.

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
[rv]: https://github.com/getsentry/raven-python
[cpuid]: https://github.com/workhorsy/py-cpuinfo
[sv]: https://pypi.python.org/pypi/semantic_version
[rq]: https://pypi.python.org/pypi/requests
[nhs]: https://pypi.python.org/pypi/ndg-httpsclient
[pan]: https://pypi.python.org/pypi/pyasn1
[pyi]: http://pyinstaller.org/

[hl]: http://www.hard-light.net/
[win_inst]: http://dev.tproxy.de/knossos/stable/knossos.exe
