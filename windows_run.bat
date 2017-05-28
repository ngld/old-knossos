@echo off

cd %~dp0
set "PATH=%PATH%;%CD%\releng\windows\support"

if exist build.ninja goto :build

py -3 configure.py
if errorlevel 1 goto :error

:build
ninja debug
goto :eof

:error
echo.
pause
