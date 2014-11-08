## Copyright 2014 Knossos authors, see NOTICE file
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
import re
import semantic_version

from .qt import QtCore, QtNetwork, QtWebKit
from . import center, api, repo, windows


class WebBridge(QtCore.QObject):

    # NOTE: Update https://github.com/ngld/knossos/wiki/JS%20API whenever you make an API change.
    # getVersion(): str
    #   Returns Knossos's version
    # isFsoInstalled(): bool
    #   Returns true if fs2_open is installed and configured.
    # isFs2PathSet(): bool
    #   Returns true if the path to the FS2 directory is set.
    # selectFs2path(): void
    #   Prompts the user to select their FS2 directory.
    # runGogInstaller(): void
    #   Launches the GOGExtract wizard.
    # getInstalledMods(): list of mod objects
    #   Returns a list of all installed mods (see the generated section of schema.txt)
    # getUpdates(): object
    #   Returns a map which follows this syntax: result[mid][local_version] = most_recent_version
    # isInstalled(mid, spec?): bool
    #   Returns true if the given mod is installed. The parameters are the same as query()'s.
    # query(mid, spec?): mod object
    #   Allows the web page to query the local mod cache. The first parameter is the mod ID.
    #   The second parameter is optional and can specify a version requirement. (i.e. ">=3.0.*")
    #   If no matching mod is found, null is returned.
    # fetchModlist(): void
    #   Update the local mod cache.
    # addRepo(name, link): void
    #   Adds a new repository.
    # getRepos(): list of [<name>, <link>]
    #   Returns a list of all configured repositories.
    # install(mid, spec?, pkgs?): int
    #   Installs the given mod. The first two parameters are the same as query()'s.
    #   The third parameter is optional and contains the names of all packages which should be installed (defaults to all required).
    #   Returns -1 if the mod wasn't found, -2 if some of the given packages are missing, 0 if the install failed and 1 on success.
    # uninstall(mid, pkgs?): bool
    #   Uninstalls the given mod. The first parameter is the mod's ID. The second parameter should be used if only some packages should be uninstalled.
    #   Returns true on success.
    # runMod(mid): void
    #   Launch fs2_open with the given mod selected.
    # showSettings(mid?): void
    #   Open the settings window for the given mod or fs2_open if no mid is given.
    # vercmp(a, b): int
    #   Compares two versions
    
    repoUpdated = QtCore.Signal()
    updateModlist = QtCore.Signal('QVariantMap', str)
    modProgress = QtCore.Signal(str, float, str)

    def __init__(self):
        super(WebBridge, self).__init__()

        center.signals.repo_updated.connect(self.repoUpdated.emit)

    @QtCore.Slot(result=str)
    def getVersion(self):
        return center.VERSION

    @QtCore.Slot(result=bool)
    def isFsoInstalled(self):
        return api.is_fso_installed()

    @QtCore.Slot(result=bool)
    def isFs2PathSet(self):
        return center.settings['fs2_path'] is not None

    @QtCore.Slot()
    def selectFs2path(self):
        api.select_fs2_path()

    @QtCore.Slot()
    def runGogInstaller(self):
        windows.GogExtractWindow()

    @QtCore.Slot(result='QVariantList')
    def getMods(self):
        return center.settings['mods'].get()

    @QtCore.Slot(result='QVariantList')
    def getInstalledMods(self):
        return center.installed.get()

    @QtCore.Slot(result='QVariantMap')
    def getUpdates(self):
        updates = center.installed.get_updates()
        result = {}
        for mid, items in updates.items():
            versions = result[mid] = {}
            for ver_a, ver_b in items.items():
                versions[str(ver_a)] = str(ver_b)

        return result

    @QtCore.Slot(str, result=bool)
    @QtCore.Slot(str, str, result=bool)
    def isInstalled(self, mid, spec=None):
        if spec is None:
            return mid in center.installed.mods
        else:
            spec = semantic_version.Spec(spec)
            mod = center.installed.mods.get(mid, None)
            if mod is None:
                return False

            return spec.match(mod.version)

    @QtCore.Slot(str, result='QVariantMap')
    @QtCore.Slot(str, str, result='QVariantMap')
    def query(self, mid, spec=None):
        if spec is not None:
            if spec == '':
                spec = None
            else:
                if re.search(r'^\d+', spec):
                    spec = '==' + spec

                try:
                    spec = semantic_version.Spec(spec)
                except:
                    logging.exception('Invalid spec "%s" passed to query()!', spec)
                    return -2

        try:
            return center.settings['mods'].query(mid, spec).get()
        except:
            return None

    @QtCore.Slot()
    def fetchModlist(self):
        api.fetch_list()

    @QtCore.Slot(str, str)
    def addRepo(self, repo_url, repo_name):
        repos = center.settings['repos']
        repos.append((repo_url, repo_name))

        api.save_settings()
        if center.main_win is not None:
            center.main_win.update_repo_list()

    @QtCore.Slot(result='QVariantList')
    def getRepos(self):
        return center.settings['repos']

    def _get_mod(self, mid, spec=None, mod_repo=None):
        if spec is not None:
            if spec == '':
                spec = None
            else:
                if re.search(r'^\d+', spec):
                    spec = '==' + spec

                try:
                    spec = semantic_version.Spec(spec)
                except:
                    logging.exception('Invalid spec "%s" passed to a web API function!', spec)
                    return -2

        if mod_repo is None:
            mod_repo = center.installed

        try:
            return mod_repo.query(mid, spec)
        except repo.ModNotFound:
            logging.exception('Couldn\'t find mod "%s" (%s)!', mid, spec)
            return -1

    @QtCore.Slot(str, result=int)
    @QtCore.Slot(str, str, result=int)
    @QtCore.Slot(str, str, 'QStringList', result=int)
    def install(self, mid, spec=None, pkgs=None):
        mod = self._get_mod(mid, spec, center.settings['mods'])
        if mod in (-1, -2):
            return mod

        windows.ModInstallWindow(mod, pkgs)

    @QtCore.Slot(str, result=int)
    @QtCore.Slot(str, str, result=int)
    @QtCore.Slot(str, str, 'QStringList', result=int)
    def uninstall(self, mid, spec=None, pkgs=None):
        mod = self._get_mod(mid, spec)
        if mod in (-1, -2):
            return mod

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

    @QtCore.Slot(str, str)
    def abortDownload(self, mid, version):
        if hasattr(center.main_win, 'abort_mod_dl'):
            center.main_win.abort_mod_dl(mid)

    @QtCore.Slot(str, result=int)
    @QtCore.Slot(str, str, result=int)
    def runMod(self, mid, spec=None):
        mod = self._get_mod(mid, spec)
        if mod in (-1, -2):
            return mod

        api.run_mod(mod)

    @QtCore.Slot(result=int)
    @QtCore.Slot(str, result=int)
    @QtCore.Slot(str, str, result=int)
    def showSettings(self, mid=None, spec=None):
        if mid is None:
            windows.SettingsWindow(None)
        else:
            mod = self._get_mod(mid, spec)
            if mod in (-1, -2):
                return mod

            windows.FlagsWindow(center.main_win.win, mod)

    @QtCore.Slot(str, str, result=int)
    def vercmp(self, a, b):
        try:
            a = semantic_version.Version(a)
            b = semantic_version.Version(b)
        except:
            #logging.exception('Someone passed an invalid version to vercmp()!')
            return 0

        return a.__cmp__(b)


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
            path = url.path()

            if path.startswith('/logo'):
                path = path.split('/')
                try:
                    mod = center.settings['mods'].query(path[2], semantic_version.Spec('==' + path[3]))
                except:
                    try:
                        mod = center.installed.query(path[2], semantic_version.Spec('==' + path[3]))
                    except:
                        mod = None

                if mod is not None:
                    url.setPath(mod.logo_path)
            else:
                url.setPath(os.path.join(center.settings_path, os.path.basename(url.path())))

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
        frame.javaScriptWindowObjectCleared.connect(self.insert_bridge)

        webView.load(QtCore.QUrl('qrc:///html/welcome.html'))

    def insert_bridge(self):
        frame = self._view.page().mainFrame()
        frame.addToJavaScriptWindowObject('fs2mod', self._bridge)

    def get_bridge(self):
        return self._bridge
