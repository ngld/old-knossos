# Preparation

* Download curl (https://curl.haxx.se/download.html#Win32) and place the curl.exe in the support directoy.
* Download 7-zip (http://7-zip.org) and place the 7z.exe and 7z.dll in the support directory.
* Download and install the latest Python 3.5 relase. The default settings are fine. (https://www.python.org/downloads/windows/)
  Once PyInstaller supports newer Python versions, we can upgrade.
* Install the Microsoft Visual C++ 2010 Redistributable Package (https://www.microsoft.com/en-au/download/details.aspx?id=5555)
* Install the Microsoft Visual C++ 2015 Redistributable Package (https://www.microsoft.com/en-us/download/details.aspx?id=53587)
* Install NSIS (http://nsis.sourceforge.net/Download)
* Download and unpack nsProcess in NSIS' Plugins directory (https://dev.tproxy.de/mirror/nsProcess_1_6.7z)
* Run fetch_support.bat

# Build

Double click on build.bat. The installer and updater will be in the dist directory. The Knossos subfolder contains the built program.