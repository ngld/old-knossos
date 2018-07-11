if not "%APPVEYOR_REPO_TAG_NAME%" == "" appveyor UpdateBuild -Version "%APPVEYOR_REPO_TAG_NAME%"

set "PATH=C:\Python36;C:\Python36\Scripts;%CD%\releng\windows\support;%PATH%"

pip install pipenv
pipenv install --system --deploy

:: Custom pyinstaller build. Hopefully causes less issues with AV software than the official prebuilt binaries.
curl -Lo pyi.7z https://d.gruenprint.de/GBGYJD3IhcnrxjNiPTJKG7fMpR1xU4Lv.7z
7z x pyi.7z
del pyi.7z

cd pyinstaller
python setup.py install
cd ..
rd /S /Q pyinstaller

python tools/common/download_archive.py releng/windows/support/support.json
yarn
