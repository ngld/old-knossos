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

from __future__ import absolute_import, print_function

import logging
import re
import semantic_version

from .qt import QtCore, QtWebChannel
from . import center, api, repo, windows, tasks, util

if not QtWebChannel:
    from .qt import QtWebKit


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
    # getMods(): list of mod objects
    #   Returns a list of all available mods (see the generated section of schema.txt).
    # getInstalledMods(): list of mod objects
    #   Returns a list of all installed mods (see the generated section of schema.txt).
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
    # abortDownload(mid): void
    #   Aborts the download for the given mod.
    # runMod(mid): void
    #   Launch fs2_open with the given mod selected.
    # showSettings(mid?): void
    #   Open the settings window for the given mod or fs2_open if no mid is given.
    #   Returns -1 if the mod wasn't found, -2 if the spec is invalid and 1 on success.
    # showPackageList(mid, spec?): int
    #   Open a window which allows the user to install and uninstall packages for the given mod.
    #   Returns -1 if the mod wasn't found, -2 if the spec is invalid and 1 on success.
    # vercmp(a, b): int
    #   Compares two versions

    updateModlist = QtCore.Signal('QVariantMap', str)
    modProgress = QtCore.Signal(str, float, str)

    taskStarted = QtCore.Signal(float, str)
    taskProgress = QtCore.Signal(float, float, str, str)
    taskFinished = QtCore.Signal(float)

    def __init__(self, webView=None):
        super(WebBridge, self).__init__()

        if QtWebChannel:
            self.bridge = self
            page = webView.page()
            channel = QtWebChannel.QWebChannel(page)

            page.setWebChannel(channel)
            channel.registerObject('fs2mod', self)

            webView.load(QtCore.QUrl('qrc:///html/welcome.html'))

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
        return list(center.mods.get())

    @QtCore.Slot(result='QVariantList')
    def getInstalledMods(self):
        return list(center.installed.get())

    @QtCore.Slot(result='QVariantMap')
    def getUpdates(self):
        updates = center.installed.get_updates()
        result = {}
        for mid, items in updates.items():
            versions = result[mid] = {}
            for ver_a, ver_b in items.items():
                versions[str(ver_a)] = str(ver_b)

        return result

    @QtCore.Slot(str, str, result=bool)
    def isInstalled(self, mid, spec=None):
        if spec is None:
            return mid in center.installed.mods
        else:
            spec = util.Spec(spec)
            mod = center.installed.mods.get(mid, None)
            if mod is None:
                return False

            return spec.match(mod.version)

    @QtCore.Slot(str, str, result='QVariantMap')
    def query(self, mid, spec=None):
        if spec is not None:
            if spec == '':
                spec = None
            else:
                if re.search(r'^\d+', spec):
                    spec = '==' + spec

                try:
                    spec = util.Spec(spec)
                except:
                    logging.exception('Invalid spec "%s" passed to query()!', spec)
                    return -2

        try:
            return center.mods.query(mid, spec).get()
        except:
            return None

    @QtCore.Slot()
    def fetchModlist(self):
        api.fetch_list()

    @QtCore.Slot(bool, result='QVariantList')
    def requestModlist(self, async=False):
        if async:
            center.main_win.update_mod_list()
            return [None]
        else:
            return list(center.main_win.search_mods())

    @QtCore.Slot(str, str)
    def addRepo(self, repo_url, repo_name):
        repos = center.settings['repos']
        repos.append((repo_url, repo_name))

        api.save_settings()
        if center.main_win is not None:
            center.main_win.update_repo_list()

    @QtCore.Slot(result='QVariantList')
    def getRepos(self):
        return list(center.settings['repos'])

    def _get_mod(self, mid, spec=None, mod_repo=None):
        if spec is not None:
            if spec == '':
                spec = None
            else:
                if re.search(r'^\d+', spec):
                    spec = '==' + spec

                try:
                    spec = util.Spec(spec)
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

    @QtCore.Slot(str, str, result=int)
    def showInfo(self, mid, spec=None):
        mod = self._get_mod(mid, spec, center.mods)
        if mod in (-1, -2):
            return mod

        windows.ModInfoWindow(mod)
        return 0

    @QtCore.Slot(str, str, 'QStringList', result=int)
    def install(self, mid, spec=None, pkgs=None):
        mod = self._get_mod(mid, spec, center.mods)
        if mod in (-1, -2):
            logging.debug('fs2mod.install(%s, %s) = %d', mid, spec, mod)
            return mod

        if pkgs is None:
            pkgs = []
        windows.ModInstallWindow(mod, pkgs)
        return 0

    @QtCore.Slot(str, str, 'QStringList', result=int)
    def uninstall(self, mid, spec=None, pkgs=None):
        mod = self._get_mod(mid, spec)
        if mod in (-1, -2):
            return mod

        if len(pkgs) == 0:
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

    @QtCore.Slot(str, str, result=int)
    def updateMod(self, mid, spec=None):
        mod = self._get_mod(mid, spec)

        if mod in (-1, -2):
            return mod

        all_vers = list(center.installed.query_all(mid))
        if len(all_vers) == 1:
            # Only one version is installed, let's update it.
            tasks.run_task(tasks.UpdateTask(mod))
        else:
            # Just install the new version
            cur_pkgs = list(mod.packages)
            for i, pkg in enumerate(cur_pkgs):
                cur_pkgs[i] = center.mods.query(mod.mid, None, pkg.name)

            tasks.run_task(tasks.InstallTask(cur_pkgs, cur_pkgs[0].get_mod()))

        center.main_win.update_mod_buttons('progress')
        return 0

    @QtCore.Slot(float)
    def abortTask(self, tid):
        if hasattr(center.main_win, 'abort_task'):
            center.main_win.abort_task(int(tid))

    @QtCore.Slot(str, str, result=int)
    def runMod(self, mid, spec=None):
        mod = self._get_mod(mid, spec)
        if mod in (-1, -2):
            return mod

        api.run_mod(mod)
        return 0

    @QtCore.Slot(str, str, result=int)
    def showSettings(self, mid=None, spec=None):
        if mid is None:
            windows.SettingsWindow()
            return 1
        else:
            mod = self._get_mod(mid, spec)
            if mod in (-1, -2):
                return mod

            windows.ModSettingsWindow(mod)
            return 1

    @QtCore.Slot(str, str, result=int)
    def showPackageList(self, mid=None, spec=None):
        mod = self._get_mod(mid, spec)
        if mod in (-1, -2):
            return mod

        win = windows.ModSettingsWindow(mod)
        win.show_pkg_tab()

        return 1

    @QtCore.Slot(str, str, result=int)
    def vercmp(self, a, b):
        try:
            a = semantic_version.Version(a)
            b = semantic_version.Version(b)
        except:
            # logging.exception('Someone passed an invalid version to vercmp()!')
            return 0

        return a.__cmp__(b)


if QtWebChannel:
    BrowserCtrl = WebBridge
else:
    class BrowserCtrl(object):
        _view = None
        _nam = None
        bridge = None

        def __init__(self, webView):
            self._view = webView
            self.bridge = WebBridge(None)

            settings = webView.settings()
            settings.setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled, True)
            
            frame = webView.page().mainFrame()
            frame.javaScriptWindowObjectCleared.connect(self.insert_bridge)

            webView.load(QtCore.QUrl('qrc:///html/welcome.html'))

        def insert_bridge(self):
            frame = self._view.page().mainFrame()

            del self.bridge
            self.bridge = WebBridge()
            frame.addToJavaScriptWindowObject('fs2mod', self.bridge)
