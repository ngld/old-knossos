cd "$(dirname "$0")"
cd ../..

if [ -n "$TRAVIS_TAG" ]; then
    RELEASE=y
else
    RELEASE=n
fi
export RELEASE
export VERSION="$(python setup.py get_version)"

if [ "$TRAVIS_OS_NAME" == "osx" ]; then
    if [ "$1" == "macos" ]; then
        cd releng/macos
        bash ./auto-build.sh
    fi
else
    case "$1" in
        ubuntu)
            docker run --rm -v"$(pwd)":/build/src -u packager -e RELEASE="$RELEASE" -e VERSION="$VERSION" -e TRAVIS=y \
              ngld/knossos-builders:ubuntu bash /build/src/releng/ubuntu/auto-build.sh
            ;;

        arch)
            docker run --rm -v"$(pwd)":/build/src -u packager -e RELEASE="$RELEASE" -e VERSION="$VERSION" -e TRAVIS=y \
              ngld/knossos-builders:arch bash /build/src/releng/arch/auto-build.sh
            ;;
    esac
fi
