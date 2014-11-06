#!/bin/bash

set -e
cd "$(dirname "$0")"
export PATH="$PWD/buildenv/bin:$PATH"

PLATFORM=mac
. ../common/helpers.sh

v_set=n
while [ ! "$1" = "" ]; do
    case "$1" in
        -h|--help)
            echo "Usage: $(basename "$0") [build variant]"
            exit 0
        ;;
        *)
            if [ "$v_set" = "n" ]; then
                VARIANT="$1"
                v_set=y
            else
                error "You passed an invalid option \"$1\". I don't know what to do with that..."
                exit 1
            fi
        ;;
    esac
    shift
done
unset v_set

check_variant

if [ ! -d buildenv ]; then
    msg "Setting up a clean build environment..."
    
    mkdir buildenv
    cd buildenv

    msg2 "Installing Homebrew..."
    curl -Lo homebrew.tar.gz https://github.com/Homebrew/homebrew/tarball/master
    tar -xzf homebrew.tar.gz --strip 1
    rm homebrew.tar.gz

    cd ..
    msg2 "Installing Python, 7-zip, SDL2 and UPX..."
    brew install python p7zip sdl2 upx

    msg2 "Installing PySide..."
    msg2 "NOTE: This might take a LONG time."
    brew install --with python --without docs pyside

    msg2 "Installing Python packages..."
    pip2 install six semantic_version requests ndg-httpsclient pyasn1

    msg2 "Fixing ndg.httpsclient..."
    python2 -c 'import ndg.httpsclient;import os.path;open(os.path.join(ndg.httpsclient.__path__[0], "__init__.py"), "w").close()'

    ensure_pyinstaller
fi

msg "Building..."
ensure_pyinstaller
generate_version > version

msg2 "Running PyInstaller..."
python2 -OO ../common/pyinstaller/pyinstaller.py -y Knossos.spec

msg "Packing DMG..."
# See https://stackoverflow.com/q/96882 for a nice documentation of this procedure.

mkdir tmp
mv ../dist/Knossos.app tmp

dmg_title="Knossos $(cat version)"

hdiutil create -srcfolder tmp -volname "$dmg_title" -fs HFS+ \
      -fsargs "-c c=64,a=16,e=16" -format UDRW pack.temp.dmg

rm -rf tmp

device="$(hdiutil attach -readwrite -noverify -noautoopen pack.temp.dmg | \
         egrep '^/dev/' | sed 1q | awk '{print $1}')"

sleep 3

echo '
   tell application "Finder"
     tell disk "'${dmg_title}'"
           open
           set current view of container window to icon view
           set toolbar visible of container window to false
           set statusbar visible of container window to false
           set the bounds of container window to {400, 100, 885, 430}
           set theViewOptions to the icon view options of container window
           set arrangement of theViewOptions to not arranged
           set icon size of theViewOptions to 72
           make new alias file at container window to POSIX file "/Applications" with properties {name:"Applications"}
           set position of item "Knossos" of container window to {100, 100}
           set position of item "Applications" of container window to {375, 100}
           close
           open
           update without registering applications
           delay 5
           close
     end tell
   end tell
' | osascript

chmod -Rf go-w /Volumes/"${dmg_title}"
sync
sync
hdiutil detach "${device}"

msg2 "Compressing DMG..."
hdiutil convert pack.temp.dmg -format UDZO -imagekey zlib-level=9 -o "Knossos.dmg"
rm -f pack.temp.dmg

msg "Done!"
