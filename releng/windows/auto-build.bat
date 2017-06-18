@echo off

cd %~dp0..\..
set "PATH=%PATH%;%CD%\releng\windows\support"

echo ==> Configuring...
py -3 configure.py
if errorlevel 1 exit /b 1

echo ==> Building...

:build
ninja installer
