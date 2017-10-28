@echo off

cd %~dp0..\..
set "PATH=%CD%\releng\windows\support;%CD%\releng\windows\support\x64;%PATH%"

if exist releng\windows\dist rmdir /S /Q releng\windows\dist
mkdir releng\windows\dist

echo ==^> Updating dependencies...
py -3 tools\common\download_archive.py releng/windows/support/support.json
py -3 tools\common\npm_wrapper.py

echo ==^> Configuring...
py -3 configure.py
if errorlevel 1 exit /b 1

echo ==^> Building...
ninja installer
