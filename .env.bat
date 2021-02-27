set "PATH=%CD%\.tools;%CD%\third_party\go\bin;%CD%\third_party\protoc-dist;%CD%\third_party\nodejs\bin;%CD%\third_party\ninja;%PATH%"

if "%CI%" == "true" (
    set "PATH=C:\msys64\mingw64\bin;%PATH%"
)
