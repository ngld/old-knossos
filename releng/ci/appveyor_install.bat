if not "%APPVEYOR_REPO_TAG_NAME%" == "" appveyor UpdateBuild -Version "%APPVEYOR_REPO_TAG_NAME%"

set "PATH=C:\Python36;C:\Python36\Scripts;%PATH%"

pip install -U pip
pip install PyQt5 six requests requests_toolbelt ply raven semantic_version pypiwin32 pyinstaller etaprogress token_bucket
pip install comtypes

python tools/common/download_archive.py releng/windows/support/support.json
npm install