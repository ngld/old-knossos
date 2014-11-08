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

error() {
    local mesg=$1
    shift
    printf "${RED}==> ERROR:${ALL_OFF}${BOLD} ${mesg}${ALL_OFF}\n" "$@" >&2
}

has() {
    which "$@" > /dev/null 2>&1
}

download() {
    if [ -f "$1" ]; then
        # Do nothing.
        msg2 "Skipped $1 because it has already been downloaded."
    elif has wget; then
        wget -O "$1" "$2"
    elif has curl; then
        curl -# -o "$1" "$2"
    else
        echo "I need curl or wget!"
        exit 1
    fi
}

check_variant() {
    if [ -z "$VARIANT" ]; then
        VARIANT="develop"
        msg "No variant specified. Assuming $VARIANT."
    else
        if [ ! "$VARIANT" = "stable" ] && [ ! "$VARIANT" = "develop" ]; then
            error "Invalid variant sepcified! Valid variants are: stable, develop"
            exit 1
        fi
    fi
}

generate_version() {
    local build_num="0"

    local last_version="$(curl -s "${UPDATE_SERVER}/${VARIANT}/version")"
    local my_version="$(grep VERSION ../../knossos/center.py | cut -d "'" -f 2)"
    local next_version="$my_version"

    local last_vnum="$(echo "$last_version" | cut -d '-' -f 1)"
    local my_vnum="$(echo "$my_version" | cut -d '-' -f 1)"

    if [ "$last_vnum" = "$my_vnum" ]; then
        build_num="$(echo "$last_version" | cut -d '-' -f 2 | cut -d . -f 2)"
        build_num=$(( $build_num + 1 ))
    fi

    if [ "$VARIANT" = "develop" ]; then
        local commit="$(git log | head -1 | cut -d " " -f 2 | cut -b -7)"
        next_version="${my_version}.${build_num}+${commit}"
    else
        if [ ! "$build_num" = "0" ]; then
            error "This version has already been released!"
            exit 1
        fi
    fi

    echo "$next_version"
}

ensure_pyinstaller() {
    if [ ! -d ../common/pyinstaller ]; then
        msg2 "Downloading PyInstaller..."
        git clone "https://github.com/pyinstaller/pyinstaller" ../common/pyinstaller
    fi
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

PLATFORM="${PLATFORM:-unknown}"
UPDATE_SERVER="https://dev.tproxy.de/knossos"
VARIANT=""