@echo off

cd %~dp0..\..

cscript \Windows\system32\slmgr.vbs /ato

echo ::: Installing Chocolatey...
powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"
SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

echo ::: Installing packages...
choco install -y --no-progress hashdeep

rem We're stuck with Python 3.5.x until PyInstaller supports Python 3.6
powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.5.3/python-3.5.3.exe', 'py3inst.exe')" <NUL
echo ecce2576a037e6e3c6ff5a5657a01996f1f62df6dc9c944965526d27405a27ee  py3inst.exe > py.hash
sha256deep -m py.hash py3inst.exe
if errorlevel 1 (
	echo Hash mismatch for Python3!
	exit /b 1
)

py3inst /quiet InstallAllUsers=1 PrependPath=1
del py3inst.exe py.hash

rem choco install -y --no-progress --x86 python3 --version 3.5.2
choco install -y --no-progress --x86 vcredist2010 vcredist2015 nsis

echo ::: Installing python dependencies...
py -3 -mpip install -U pip
py -3 -mpip install PyQt5 six requests requests_toolbelt ply raven semantic_version pypiwin32 comtypes pyinstaller etaprogress

echo ::: Downloading remaining dependencies...
py -3 tools/common/download_archive.py releng/windows/support/support.json

call npm install
