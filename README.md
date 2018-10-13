# A mod manager

A modern mod manager and launcher for FreeSpace Open

## Website

[**Installation instructions**](https://fsnebula.org/knossos/)

## Dependencies

To run this script you'll need the following:
* [Python][py] 2 or 3
* [SDL2][sdl2]
* [OpenAL][oal]
* [7zip][7z] (IMPORTANT: This script needs the full implementation, i.e. ```p7zip-full``` _and_ ```p7zip-rar``` on Ubuntu)
* [pipenv][pipenv]
* [yarn][yarn]
* [ninja][ninja]

To install the Python and JavaScript dependencies run the following commands:

```bash
pipenv install
yarn install
```

If you're on Windows, the `windows_run.bat` file will take care of this in addition to launching Knossos itself.


## Usage

After your first checkout you will have to run the two commands above and `pipenv run python configure.py` once. If it aborts before displaying `Writing build.ninja...`, you have to fix the error before you can continue.
If it complains that ```rcc``` is missing, you will need to install the developer packages for Qt5.

Now you can use `ninja run` to launch Knossos in release mode and `ninja debug` to launch it in debug mode. In debug mode you can use a chromium-based browser to access the DevTools by navigating to http://localhost:4006/.

If you add or remove files in `knossos`, `html/templates` or `html/images`, you need to run `tools/common/update_file_list.py` (or `update_file_list.bat` on Windows) to update `file_list.json`.

## License

Licensed under the Apache License, Version 2.0.
See the [NOTICE](NOTICE) file for information.

The icon is borrowed from [Hard Light][hl].

[py]: http://www.python.org/
[qt]: http://www.qt.io/
[sdl2]: https://libsdl.org/download-2.0.php
[oal]: http://kcat.strangesoft.net/openal.html
[7z]: http://www.7-zip.org/
[pipenv]: https://pipenv.readthedocs.io/en/latest/
[yarn]: https://yarnpkg.com/en/
[ninja]: https://ninja-build.org/

[hl]: https://www.hard-light.net/
