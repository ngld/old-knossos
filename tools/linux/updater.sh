## Copyright 2015 Knossos authors, see NOTICE file
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

set -e

## Settings

variant="${KN_VARIANT:-develop}"
server="https://dev.tproxy.de/knossos/$variant"
archive="$server/linux.tar.gz"

## End Settings

msg() {
    local mesg=$1
    shift
    printf "${GREEN}==>${ALL_OFF}${BOLD} ${mesg}${ALL_OFF}\n" "$@" >&2
}

msg2() {
    local mesg=$1
    shift
    printf "${BLUE}  ->${ALL_OFF}${BOLD} ${mesg}${ALL_OFF}\n" "$@" >&2
}

msg3() {
    local mesg=$1
    shift
    printf "    ${BOLD} ${mesg}${ALL_OFF}\n" "$@" >&2
}

error() {
    local mesg=$1
    shift
    printf "${RED}==> ERROR:${ALL_OFF}${BOLD} ${mesg}${ALL_OFF}\n" "$@" >&2
}

warning() {
    local mesg=$1
    shift
    printf "${YELLOW}==> WARNING:${ALL_OFF}${BOLD} ${mesg}${ALL_OFF}\n" "$@" >&2
}

has() {
    which "$@" > /dev/null 2>&1
}

pushd() {
    command pushd "$@" > /dev/null
}

popd() {
    command popd "$@" > /dev/null
}

download() {
    if has wget; then
        wget -O "$1" "$2"
    elif has curl; then
        msg2 "Downloading $1..."
        curl -# -o "$1" "$2"
    else
        error "I need curl or wget!"
        exit 1
    fi
}

get() {
    if has curl; then
        curl -s "$1"
    elif has wget; then
        wget -q -O- "$1"
    else
        error "I need curl or wget!"
        exit 1
    fi
}

sudo_do() {
    msg3 "sudo $*"
    sudo "$@"
}

# prefer terminal safe colored and bold text when tput is supported
if tput setaf 0 &>/dev/null; then
    ALL_OFF="$(tput sgr0)"
    BOLD="$(tput bold)"
    BLUE="${BOLD}$(tput setaf 4)"
    GREEN="${BOLD}$(tput setaf 2)"
    RED="${BOLD}$(tput setaf 1)"
    YELLOW="${BOLD}$(tput setaf 3)"
else
    ALL_OFF="\e[1;0m"
    BOLD="\e[1;1m"
    BLUE="${BOLD}\e[1;34m"
    GREEN="${BOLD}\e[1;32m"
    RED="${BOLD}\e[1;31m"
    YELLOW="${BOLD}\e[1;33m"
fi


msg "Updating Knossos..."
msg2 "Looking for python..."

if has python3; then
    PYTHON="python3"
elif has python; then
    PYTHON="python"
else
    error "You don't have Python installed! I can only update an existing Knossos installations!"
    exit 1
fi

msg2 "Looking for existing Knossos installation..."

script="
import sys
import os.path
try:
    import knossos
except ImportError:
    print('#')
else:
    print(os.path.dirname(knossos.__file__))
"
knossos_path="$($PYTHON -c "$script")"

if [ "$knossos_path" = "#" ]; then
    if [ -d /usr/share/knossos ]; then
        knossos_path="/usr/share/knossos/knossos"
    else
        error "Couldn't find an existing Knossos installation!"
        exit 1
    fi
fi

if [ ! -d "$knossos_path" ]; then
    if [ -z "$knossos_path" ]; then
        error "Couldn't find an existing Knossos installation!"
        exit 1
    else
        error "I thought Knossos was in $knossos_path but I guess I'm wrong!"
        exit 1
    fi
fi

if [ ! "$(basename "$knossos_path")" = "knossos" ]; then
    warning "Found Knossos in $knossos_path but the directory isn't called \"knossos\"!"
else
    msg3 "Found Knossos in $knossos_path"
fi

msg2 "Downloading..."
arpath="$(mktemp "${TMPDIR:-/tmp}/XXXXXXXXX.tar.gz")"

# Make sure we clean up
trap '[ -f "$arpath" ] && rm "$arpath"' EXIT
download "$arpath" "$server/knossos.tar.gz"

msg2 "Unpacking..."
sudo_do tar -xzf "$arpath" -C "$knossos_path" --strip 1

msg "Done!"
