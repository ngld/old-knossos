if "%APPVEYOR_REPO_TAG_NAME%" == "" goto :eof

set "PATH=C:\Python36;C:\Python36\Scripts;%PATH%"

pip install githubrelease
githubrelease asset ngld/knossos upload "%APPVEYOR_REPO_TAG_NAME%" releng/windows/dist/*.exe
