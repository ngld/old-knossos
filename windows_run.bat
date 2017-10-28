@echo off

cd %~dp0
set "PATH=%PATH%;%CD%\releng\windows\support;%CD%\releng\windows\support\x64"

:: Update the Windows dependencies if necessary.
py -3 tools\common\download_archive.py releng\windows\support\support.json

:: Run "npm install" if necessary.
py -3 tools\common\npm_wrapper.py

if exist build.ninja goto :build

py -3 configure.py
if errorlevel 1 goto :error

:build
ninja debug
if errorlevel 1 goto :error
goto :eof

:error
echo.
pause
