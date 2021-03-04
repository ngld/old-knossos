@echo off

setlocal
cd %~dp0

go version > NUL 2>&1
if errorlevel 1 goto :fix_go
goto :build

:fix_go
if not exist third_party\go\bin\go.exe call :fetch_go
if not exist third_party\go\bin\go.exe goto :no_go

:build
if not exist .tools\tool.exe call :install_tools

.tools\tool.exe task %*
goto :eof

:fetch_go
echo Downloading Go toolchain...

if not exist third_party mkdir third_party
cd third_party

curl -Lo go.zip "https://golang.org/dl/go1.15.8.windows-amd64.zip"

echo Unpacking...
tar -xzf go.zip
del go.zip
cd ..

goto :eof

:no_go
echo Could not find or fetch Go!
echo.
echo Please install the Go toolchain or fix the previous error
echo and try again.
echo.
pause

goto :eof

:install_tools
cd packages\build-tools
echo Building build-tools...
go build -o ..\..\.tools\tool.exe
cd ..\..

goto :eof

