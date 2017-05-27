@echo off

cd %~dp0..\..

echo ==> Installing Chocolatey...
powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"
SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

echo ==> Installing packages...
rem We're stuck with Python 3.5.x until PyInstaller supports Python 3.6
choco install -y --no-progress python3 --version 3.5.2
choco install -y --no-progress vcredist2010 nsis

echo ==> Installing python dependencies...
py -3 -mpip install -U pip
py -3 -mpip install PyQt5 six requests semantic_version pypiwin32 comtypes pyinstaller etaprogress

echo ==> Downloading remaining dependencies...
py -3 tools/common/download_archive.py releng/windows/support/support.json
