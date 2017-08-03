@echo off

cd %~dp0..\..
set "PATH=%CD%\releng\windows\support;%PATH%"

if exist releng\windows\dist rmdir /S /Q releng\windows\dist
mkdir releng\windows\dist

echo ==^> Configuring...
py -3 configure.py
if errorlevel 1 exit /b 1

echo ==^> Building...

:build
ninja installer
