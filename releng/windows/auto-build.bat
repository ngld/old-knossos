@echo off

cd \

if exist knossos goto :update

echo ==^> Cloning knossos...
git clone knossos_src knossos

goto :sync_changes

:update

echo ==^> Updating knossos...
cd knossos

git reset --hard
git pull

:sync_changes

echo ==^> Syncing changes...
cd \knossos_src
git diff > \knossos\pp

cd \knossos
git apply pp
del pp

set "PATH=%CD%\releng\windows\support;%CD%\releng\windows\support\x64;%PATH%"

if exist releng\windows\dist rmdir /S /Q releng\windows\dist
mkdir releng\windows\dist

echo ==^> Updating dependencies...
python tools\common\download_archive.py releng/windows/support/support.json
python tools\common\npm_wrapper.py

echo ==^> Configuring...
python configure.py
if errorlevel 1 exit /b 1

echo ==^> Building...
ninja installer
