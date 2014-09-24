## Copyright 2014 fs2mod-py authors, see NOTICE file
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

import os
import logging
import semantic_version

from .qt import QtCore, QtNetwork, QtWebKit
from . import api
from .windows import FlagsWindow, SettingsWindow, GogExtractWindow
import manager


class WebBridge(QtCore.QObject):

    # getVersion(): Returns fs2mod-py's version
    # isFsoInstalled(): Returns true if fs2_open is installed and configured.
    # getInstalledMods(): Returns a list of all installed mods (see the generated section of schema.txt)
    # isInstalled(mid, spec?): Returns true if the given mod is installed. The parameters are the same as query()'s.
    # query(mid, spec?): Allows the web page to query the local mod cache. The first parameter is the mod ID. The second parameter is optional and can specify a version requirement. (i.e. ">=3.0.*")
    # fetchModlist(): Update the local mod cache.
    # install(mid, spec?, pkgs?): Installs the given mod. The first two parameters are the same as query()'s. The third parameter is optional and contains the names of all packages which should be installed (defaults to all required).
    # uninstall(mid, pkgs?): Uninstalls the given mod. The first parameter is the mod's ID. The second parameter should be used if only some packages should be uninstalled.
    # runMod(mid): Launch fs2_open with the given mod selected.
    # showSettings(mid?): Open the settings window for the given mod or fs2_open if no mid is given.
    
    repoUpdated = QtCore.Signal()

    def __init__(self):
        super(WebBridge, self).__init__()

        manager.signals.repo_updated.connect(self.repoUpdated.emit)

    @QtCore.Slot(result=str)
    def getVersion(self):
        return manager.VERSION

    @QtCore.Slot(result=bool)
    def isFsoInstalled(self):
        return api.is_fso_installed()

    @QtCore.Slot(result=bool)
    def isFs2PathSet(self):
        return manager.settings['fs2_path'] is not None

    @QtCore.Slot()
    def selectFs2path(self):
        manager.select_fs2_path()

    @QtCore.Slot()
    def runGogInstaller(self):
        GogExtractWindow(manager.main_win)

    @QtCore.Slot(result='QVariantList')
    def getInstalledMods(self):
        return manager.installed.get()

    @QtCore.Slot(str, result=bool)
    @QtCore.Slot(str, str, result=bool)
    def isInstalled(self, mid, spec=None):
        if spec is None:
            return mid in manager.installed.mods
        else:
            spec = semantic_version.Spec(spec)
            mod = manager.installed.mods.get(mid, None)
            if mod is None:
                return False

            return spec.match(mod.version)

    @QtCore.Slot(str, result='QVariantMap')
    @QtCore.Slot(str, str, result='QVariantMap')
    def query(self, mid, spec=None):
        if spec is not None:
            spec = semantic_version.Spec(spec)

        try:
            return manager.settings['mods'].query(mid, spec).get()
        except:
            return None

    @QtCore.Slot()
    def fetchModlist():
        manager.fetch_list()

    @QtCore.Slot(str, result=int)
    @QtCore.Slot(str, str, result=int)
    @QtCore.Slot(str, str, 'QStringList', result=int)
    def install(self, mid, spec=None, pkgs=None):
        if spec is not None:
            spec = semantic_version.Spec(spec)

        try:
            mod = manager.settings['mods'].query(mid, spec)
        except:
            logging.exception('Couldn\'t find mod "%s"!', mid)
            return -1

        if pkgs is None:
            plist = mod.resolve_deps()
        else:
            plist = []
            pfound = set()
            for pkg in mod.packages:
                if pkg.name in pkgs:
                    plist.append(pkg)
                    pfound.add(pkg.name)

            if len(pfound) < len(pkgs):
                # Some packages are missing
                pmissing = set(pkgs) - pfound
                logging.warning('Missing packages %s.', ', '.join(pmissing))
                return -2

        return api.install_pkgs(plist, name=mod.title)

    @QtCore.Slot(str, result=bool)
    @QtCore.Slot(str, 'QStringList', result=bool)
    def uninstall(self, mid, pkgs=None):
        if mid not in manager.installed.mods:
            logging.exception('Couldn\'t find mod "%s"!', mid)
            return -1

        mod = manager.installed.mods[mid]

        if pkgs is None:
            plist = mod.packages
        else:
            plist = []
            pfound = set()
            for pkg in mod.packages:
                if pkg.name in pkgs:
                    plist.append(pkg)
                    pfound.add(pkg.name)

            if len(pfound) < len(pkgs):
                # Some packages are missing
                pmissing = set(pkgs) - pfound
                logging.warning('Missing packages %s.', ', '.join(pmissing))
                return -2

        return api.uninstall_pkgs(plist, name=mod.title)

    @QtCore.Slot(str)
    def runMod(self, mid):
        if mid not in manager.installed.mods:
            logging.error('Couldn\'t find mod "%s"!', mid)
            return -1

        manager.run_mod(manager.installed.mods[mid])

    @QtCore.Slot()
    @QtCore.Slot(str)
    def showSettings(self, mid=None):
        if mid is None:
            SettingsWindow(None)
        else:
            if mid not in manager.installed.mods:
                logging.error('Couldn\'t find mod "%s"!', mid)
                return -1

            FlagsWindow(manager.main_win.win, manager.installed.mods[mid])


class NetworkAccessManager(QtNetwork.QNetworkAccessManager):

    def __init__(self, old_manager):
        super(NetworkAccessManager, self).__init__()

        self.old_manager = old_manager

        self.setCache(old_manager.cache())
        self.setCookieJar(old_manager.cookieJar())
        self.setProxy(old_manager.proxy())
        self.setProxyFactory(old_manager.proxyFactory())
    
    def createRequest(self, operation, request, data):
        if request.url().scheme() == 'fsrs' and operation == self.GetOperation:
            # Rewrite fsrs:// links.
            url = request.url()
            url.setScheme('file')
            url.setPath(os.path.join(manager.settings_path, os.path.basename(url.path())))

            request.setUrl(url)
        
        return super(NetworkAccessManager, self).createRequest(operation, request, data)


class BrowserCtrl(object):
    _view = None
    _bridge = None
    _nam = None

    def __init__(self, webView):
        self._view = webView
        self._bridge = WebBridge()

        settings = webView.settings()
        # settings.setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)  # May be necessary for YouTube videos...
        settings.setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled, True)
        settings.setAttribute(QtWebKit.QWebSettings.OfflineWebApplicationCacheEnabled, True)

        page = webView.page()
        self._nam = NetworkAccessManager(page.networkAccessManager())
        page.setNetworkAccessManager(self._nam)

        frame = page.mainFrame()
        frame.javaScriptWindowObjectCleared.connect(self.insertBridge)

        webView.load(QtCore.QUrl('./html/welcome.html'))

    def insertBridge(self):
        frame = self._view.page().mainFrame()
        frame.addToJavaScriptWindowObject('fs2mod', self._bridge)
