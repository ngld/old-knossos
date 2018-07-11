@echo off

cd %~dp0..\..

cscript \Windows\system32\slmgr.vbs /ato

echo ::: Installing Scoop...
powershell -NoProfile -ExecutionPolicy RemoteSigned -Command "iex (new-object net.webclient).downloadstring('https://get.scoop.sh')"
SET "PATH=%PATH%;%USERPROFILE%\scoop\shims"

call scoop install wget git
call scoop bucket add extras
call scoop bucket add versions

echo ::: Installing NSIS and Python 3.6...
call scoop install nsis
call scoop install -a 32bit python36

echo ::: Installing Windows 10 SDK...
call wget https://download.microsoft.com/download/5/A/0/5A08CEF4-3EC9-494A-9578-AB687E716C12/windowssdk/winsdksetup.exe

call winsdksetup.exe /features OptionId.DesktopCPPx86 /q
del winsdksetup.exe

echo ::: Installing python dependencies...
call python -mpip install -U pip pipenv
call python -mpipenv install --system --deploy

echo ::: Installing custom PyInstaller build...
wget -O pyi.7z https://d.gruenprint.de/GBGYJD3IhcnrxjNiPTJKG7fMpR1xU4Lv.7z
7z x pyi.7z
cd pyinstaller
call python setup.py install
cd ..
rd /S /Q pyinstaller
