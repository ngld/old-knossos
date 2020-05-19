#!/bin/bash

install_clitools(){
  ##### START from Mokacoding (https://www.mokacoding.com/blog/how-to-install-xcode-cli-tools-without-gui/)
  # See http://apple.stackexchange.com/questions/107307/how-can-i-install-the-command-line-tools-completely-from-the-command-line

  echo "Checking Xcode CLI tools"
  # Only run if the tools are not installed yet
  # To check that try to print the SDK path
  if [ xcode-select -p &> /dev/null ]; then
    echo "Xcode CLI tools OK"
  else
    echo "Xcode CLI tools not found. Installing them..."
    touch /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress;
    PROD=$(softwareupdate -l |
      grep "\*.*Command Line" |
      head -n 1 | awk -F"*" '{print $2}' |
      sed -e 's/^ *//' |
      tr -d '\n')
    softwareupdate -i "$PROD";
  fi
  ##### END from Mokacoding
}

install_nvm(){
  echo "==> Installing Node nvm"
  touch /Users/vagrant/.profile
  chown Vagrant:staff /Users/vagrant/.profile
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
  nvm install 14.1.0 # Matches current version in brew
}

install_yarn(){
  echo "==> Installing Yarn"
  curl -o- -L https://yarnpkg.com/install.sh | bash
}

install_homebrew(){
  echo "==> Installing Homebrew"
  # Pretened to be CI Bot, enables silent install, must install Dev Tools first (see above)
  CI=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
}

install_brews(){
  # Don't waste time on updating Homebrew.
  export HOMEBREW_NO_AUTO_UPDATE=1

  echo "==> Installing build tools"
  brew install --force-bottle p7zip ninja
}

install_python(){
  # We need Python 3.6 since that's the latest version PyInstaller supports.
  # Update: PyInstaller supports 3.7 now but couldn't get things to cooperate with it.
  # Also this needs to agree with the version in the Pipfile.
  echo "==> Installing Python 3.6.8"
  curl -so python.pkg "https://www.python.org/ftp/python/3.6.8/python-3.6.8-macosx10.9.pkg"
  sudo installer -store -pkg python.pkg -target /

  export PATH="/Library/Frameworks/Python.framework/Versions/3.6/bin:$PATH"
}

install_SDL2(){
  echo "==> Installing SDL2"
  curl -so SDL2.dmg "https://libsdl.org/release/SDL2-2.0.12.dmg"

  dev="$(hdiutil attach SDL2.dmg | tail -n1 | awk '{ print $3 }')"
  sudo cp -a "$dev/SDL2.framework" /Library/Frameworks
  hdiutil detach "$dev"
  rm SDL2.dmg
}

install_qt5(){
  # Visit script URL for info.  From 'Cubes' (qbs)
  echo "==> Installing Qt5 (base and tools)"
  curl -o install-qt.sh https://raw.githubusercontent.com/qbs/qbs/faa280045d783d2fbe815fa83c8c143faf02ecf7/scripts/install-qt.sh
  chmod +x install-qt.sh
  # See below URL for examples on what packages are available for a version
  # https://download.qt.io/online/qtsdkrepository/mac_x64/desktop/qt5_598/qt.qt5.598.clang_64/
  # Should agree with Pipfile PyQt5 version and path in auto-build.sh
  ./install-qt.sh --directory /usr/local/opt/Qt --version 5.10.1 qtbase qttools
  ln -s /usr/local/opt/Qt/5.10.1/clang_64 /usr/local/opt/qt5
}

install_pideps(){
  # To prevent python pipenv error during init script
  # "Click will abort further execution because Python 3 was configured to use ASCII as encoding for the environment."
  # https://click.palletsprojects.com/en/7.x/python3/
  export LC_ALL=en_US.UTF-8
  export LANG=en_US.UTF-8

  echo "==> Installing Python dependencies"
  # Seems like we need to go to the knossos folder before running pipenv
  pip3 install -U pip pipenv wheel macholib
  pipenv install --system --deploy
}
