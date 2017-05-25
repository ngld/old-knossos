@echo off

if not exist dist goto :start_build
echo Removing old dist directoy...
rmdir /S /Q dist
if errorlevel 1 goto :error

:start_build
python -OO -mPyInstaller -d --distpath=.\dist --workpath=.\build Knossos.spec -y
if errorlevel 1 goto :error

if "%KN_BUILD_DEBUG%" == "yes" goto :end

set /P kver= < version

echo Building installer...
"C:\Program Files (x86)\NSIS\makensis" /NOCD /DKNOSSOS_ROOT=..\\..\\ /DKNOSSOS_VERSION="%kver%" nsis/installer.nsi
if errorlevel 1 goto :error

echo Building updater...
"C:\Program Files (x86)\NSIS\makensis" /NOCD /DKNOSSOS_ROOT=..\\..\\ /DKNOSSOS_VERSION="%kver%" nsis/updater.nsi
if errorlevel 1 goto :error

goto :end
:error
echo Build FAILED!

:end
pause