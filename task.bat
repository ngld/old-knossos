@echo off

cd %~dp0
call .env.bat
set "root=%CD%"

go version > NUL 2>&1
if errorlevel 1 goto :fix_go
goto :build

:fix_go
if not exist third_party\go\bin\go.exe call :fetch_go
if not exist third_party\go\bin\go.exe goto :no_go

:build
if not exist .tools\task.exe call :install_tools

task.exe %*
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

echo Installing tools...
tool.exe install-tools
goto :eof

