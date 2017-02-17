@echo off

echo Looking for python...
py -3.5 -V
if errorlevel 1 goto :error

echo Looking for virtualenv...
py -3.5 -mvirtualenv -h > NUL
if not errorlevel 1 goto :skip_virtualenv

echo Trying to install virtualenv...
py -3.5 -mpip install -U pip virtualenv
if errorlevel 1 goto :error

:skip_virtualenv
if exist py-env goto :skip_env

echo Creating python environment...
mkdir py-env
mkdir py-env\Scripts
py -3.5 -c "import sys, shutil;shutil.copyfile(sys.prefix + r'\vcruntime140.dll', r'py-env\Scripts\vcruntime140.dll')"

py -3.5 -mvirtualenv py-env
:: Make sure the python3.dll is in the right place
py -3.5 -c "import sys, shutil;shutil.copyfile(sys.prefix + r'\python3.dll', r'py-env\Scripts\python3.dll')"

call py-env/Scripts/activate.bat

echo Installing dependencies...
pip install six requests semantic_version raven PyQt5 PyInstaller pypiwin32 comtypes


:skip_env
if not exist support\curl.exe goto :curl_missing
if not exist support\7z.exe goto :7z_missing

if exist support\SDL2.dll goto :skip_sdl2
echo Downloading SDL2...
support\curl -Lo sdl2.zip "https://libsdl.org/release/SDL2-2.0.5-win32-x86.zip"
if errorlevel 1 goto :error

support\7z x -osupport sdl2.zip
if errorlevel 1 goto :error
del support\README.txt
del sdl2.zip

:skip_sdl2
if exist support\openal.dll goto :skip_openal
echo Downloading OpenAL Soft...
support\curl -Lo openal.zip "http://kcat.strangesoft.net/openal-binaries/openal-soft-1.17.2-bin.zip"
if errorlevel 1 goto :error

mkdir tmp
support\7z x -otmp openal.zip
if errorlevel 1 goto :error
move tmp\openal-soft-1.17.2-bin\bin\Win32\soft_oal.dll support\openal.dll
rmdir /S /Q tmp
del openal.zip

:skip_openal
if exist py-env\Scripts\upx.exe goto :skip_upx
echo Downloading UPX...
support\curl -Lo upx.zip "https://github.com/upx/upx/releases/download/v3.93/upx393w.zip"
if errorlevel 1 goto :error

support\7z x -otmp upx.zip
move tmp\upx393w\upx.exe py-env\Scripts
rmdir /S /Q tmp
del upx.zip

:skip_upx
echo Done.
pause
goto :eof

:error
echo ERROR!
pause
goto :eof

:curl_missing
echo support\curl.exe is missing!
pause
goto :eof

:7z_missing
echo support\7z.exe is missing!
pause
goto :eof
