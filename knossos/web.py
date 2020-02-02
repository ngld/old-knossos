## Copyright 2017 Knossos authors, see NOTICE file
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

import sys
import os.path
import logging
import re
import json
import platform
import stat
import sqlite3
import shutil
import semantic_version

from threading import Thread
from datetime import datetime
from .qt import QtCore, QtGui, QtWidgets, QtWebChannel, read_file, run_in_qt
from . import center, runner, repo, windows, tasks, util, settings, nebula, clibs

if not QtWebChannel:
    from .qt import QtWebKit
else:
    class WebSocketWrapper(QtWebChannel.QWebChannelAbstractTransport):
        _conn = None
        _bridge = None

        def __init__(self, conn, bridge):
            super(WebSocketWrapper, self).__init__()

            self._bridge = bridge
            self._bridge._conns.append(self)

            self._conn = conn
            self._conn.textMessageReceived.connect(self.socketMessageReceived)
            self._conn.disconnected.connect(self.socketDisconnected)

        def sendMessage(self, msg):
            for k, v in msg.items():
                if isinstance(v, QtCore.QJsonValue):
                    msg[k] = v.toVariant()

            # print('#-> ', json.dumps(msg))
            self._conn.sendTextMessage(json.dumps(msg))

        def socketMessageReceived(self, msg):
            # print('#<- ', json.loads(msg))
            self.messageReceived.emit(json.loads(msg), self)

        def socketDisconnected(self):
            self._bridge._conns.remove(self)


class WebBridge(QtCore.QObject):
    _view = None
    _last_upload = None

    asyncCbFinished = QtCore.Signal(int, str)
    showWelcome = QtCore.Signal()
    showDetailsPage = QtCore.Signal('QVariant')
    showRetailPrompt = QtCore.Signal()
    showLaunchPopup = QtCore.Signal(str)
    showModDetails = QtCore.Signal(str)
    updateModlist = QtCore.Signal(str, str, list)
    modProgress = QtCore.Signal(str, float, str)
    retailInstalled = QtCore.Signal()
    hidePopup = QtCore.Signal()
    applyDevDesc = QtCore.Signal(str)

    taskStarted = QtCore.Signal(float, str, list)
    taskProgress = QtCore.Signal(float, float, str)
    taskFinished = QtCore.Signal(float)
    taskMessage = QtCore.Signal(str)

    fs2Launching = QtCore.Signal()
    fs2Launched = QtCore.Signal()
    fs2Quit = QtCore.Signal()

    def __init__(self, webView=None):
        super(WebBridge, self).__init__()
        self._view = webView

    def load(self):
        if QtWebChannel:
            self.bridge = self
            page = self._view.page()
            self._channel = QtWebChannel.QWebChannel(page)

            page.setWebChannel(self._channel)
            self._channel.registerObject('fs2mod', self)

            if center.DEBUG and os.path.isdir('../html'):
                from .qt import QtWebSockets, QtNetwork

                if QtWebSockets is None:
                    logging.warn('Remote mode disabled')

                    link = 'qrc:///html/index.html'
                else:
                    self._conns = []
                    self._server = QtWebSockets.QWebSocketServer('Knossos interface', QtWebSockets.QWebSocketServer.NonSecureMode)
                    if not self._server.listen(QtNetwork.QHostAddress.LocalHost, 4007):
                        logging.warn('Failed to listen on port 4007!')
                    else:
                        self._server.newConnection.connect(self._acceptConnection)

                    with open('../html/qwebchannel.js', 'w') as hdl:
                        hdl.write(read_file(':/qtwebchannel/qwebchannel.js'))

                    link = os.path.abspath('../html/index_debug.html')
                    if sys.platform == 'win32':
                        link = '/' + link.replace('\\', '/')

                    link = 'file://' + link
            else:
                link = 'qrc:///html/index.html'

            self._view.load(QtCore.QUrl(link))

    def _acceptConnection(self):
        conn = self._server.nextPendingConnection()
        self._channel.connectTo(WebSocketWrapper(conn, self))

    @QtCore.Slot('QVariantList', result=str)
    def finishInit(self, tr_keys):
        trs = {}
        for k in tr_keys:
            trs[k] = QtCore.QCoreApplication.translate('modlist_ts', k)

        center.main_win.finish_init()
        return json.dumps({
            't': trs,
            'platform': sys.platform,
            'welcome': 'KN_WELCOME' in os.environ or center.settings['base_path'] is None,
            'explore_mods': center.main_win.get_explore_mod_list_cache_json()
        })

    @QtCore.Slot(result=str)
    def getVersion(self):
        return center.VERSION

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
                except Exception:
                    logging.exception('Invalid spec "%s" passed to query()!', spec)
                    return -2

        try:
            return center.mods.query(mid, spec).get()
        except Exception:
            return None

    @QtCore.Slot()
    def fetchModlist(self):
        tasks.run_task(tasks.LoadLocalModsTask())
        tasks.run_task(tasks.FetchTask())

    @QtCore.Slot(bool, result='QVariantList')
    def requestModlist(self, async_=False):
        if async_:
            center.main_win.update_mod_list()
            return [None]
        else:
            return list(center.main_win.search_mods())

    @QtCore.Slot(str)
    def showTab(self, name):
        try:
            center.main_win.update_mod_buttons(name)
        except Exception:
            logging.exception('Failed to switch tabs!')

    @QtCore.Slot(str)
    def showMod(self, mid):
        # Make sure the mod list is puplated.
        try:
            center.main_win.update_mod_buttons('explore')
            self.showModDetails.emit(mid)
        except Exception:
            logging.exception('Failed to show mod %s!' % mid)

    @QtCore.Slot(str)
    def triggerSearch(self, term):
        center.main_win.perform_search(term)

    def _get_mod(self, mid, spec=None, mod_repo=None):
        if spec is not None:
            if spec == '':
                spec = None
            else:
                if re.search(r'^\d+', spec):
                    spec = '==' + str(semantic_version.Version.coerce(spec))

                try:
                    spec = util.Spec(spec)
                except Exception:
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
    def showAvailableDetails(self, mid, spec=None):
        mod = self._get_mod(mid, spec, center.mods)
        if mod in (-1, -2):
            return mod

        self.showDetailsPage.emit(mod.get())
        return 0

    @QtCore.Slot(str, str, result=int)
    def showInstalledDetails(self, mid, spec=None):
        mod = self._get_mod(mid, spec)
        if mod in (-1, -2):
            return mod

        self.showDetailsPage.emit(mod.get())
        return 0

    @QtCore.Slot(str, str, 'QStringList', result=int)
    def install(self, mid, spec=None, pkgs=None):
        mod = self._get_mod(mid, spec, center.mods)
        if mod in (-1, -2):
            logging.debug('fs2mod.install(%s, %s) = %d', mid, spec, mod)
            return mod

        if pkgs is None:
            pkgs = []

        if mod.parent == 'FS2':
            retail = self._get_mod('FS2')

            if retail == -1:
                self.showRetailPrompt.emit()
                return 0

        windows.ModInstallWindow(mod, pkgs)
        return 0

    @QtCore.Slot(str, str, 'QStringList', result=int)
    def uninstall(self, mid, spec=None, pkgs=None):
        mod = self._get_mod(mid, spec)
        if mod in (-1, -2):
            return mod

        if mod.dev_mode:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr("I can't uninstall this mod because it's in dev mode!"))
            return 0

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

        titles = [pkg.name for pkg in plist if center.installed.is_installed(pkg)]
        # FIXME: Check if any other mod dependes on this mod before uninstalling it to avoid broken dependencies.

        deps = center.installed.get_dependents(plist)
        if deps:
            names = sorted([m.title for m in deps])
            msg = self.tr('You can\'t uninstall this because %s still depend on it.') % util.human_list(names)
            QtWidgets.QMessageBox.critical(None, 'Knossos', msg)
            return False

        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Question)
        msg.setText(self.tr('Do you really want to uninstall %s?') % (mod.title,))

        if len(titles) > 0:
            msg.setInformativeText(self.tr('%s will be removed.') % (', '.join(titles)))

        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.No)

        if msg.exec_() == QtWidgets.QMessageBox.Yes:
            tasks.run_task(tasks.UninstallTask(plist, mods=[mod]))
            return True
        else:
            return False

    @QtCore.Slot(str, str, result=int)
    def updateMod(self, mid, spec=None):
        mod = self._get_mod(mid, spec)

        if mod in (-1, -2):
            return mod

        new_rel = center.mods.query(mod.mid)

        try:
            old_rel = center.mods.query(mod)
        except repo.ModNotFound:
            old_rel = mod

        try:
            latest_ins = center.installed.query(mod.mid).version
        except repo.ModNotFound:
            latest_ins = None

        new_opt_pkgs = set([pkg.name for pkg in new_rel.packages if pkg.status in ('recommended', 'optional')])
        old_opt_pkgs = set([pkg.name for pkg in old_rel.packages if pkg.status in ('recommended', 'optional')])

        sel_pkgs = []
        installed_pkgs = [pkg.name for pkg in mod.packages]

        for pkg in new_rel.packages:
            if pkg.status == 'required' or pkg.name in installed_pkgs:
                sel_pkgs.append(pkg)

        if new_opt_pkgs - old_opt_pkgs:
            for pkg in new_rel.packages:
                if pkg.status == 'recommended' and pkg.name not in sel_pkgs:
                    sel_pkgs.append(pkg)

        all_vers = list(center.installed.query_all(mid))
        if len(all_vers) == 1 and not mod.dev_mode:
            # Only one version is installed, let's update it.

            if new_opt_pkgs - old_opt_pkgs:
                # There are new recommended or optional packages, we'll have to ask the user.
                windows.ModInstallUpdateWindow(new_rel, mod, [p.name for p in sel_pkgs])
            else:
                if latest_ins == new_rel.version:
                    # Only metadata changed
                    tasks.run_task(tasks.RewriteModMetadata([mod]))
                else:
                    tasks.run_task(tasks.UpdateTask(mod, sel_pkgs))
        else:
            # Just install the new version
            if new_opt_pkgs - old_opt_pkgs:
                # There are new recommended or optional packages, we'll have to ask the user.
                windows.ModInstallWindow(new_rel, [p.name for p in sel_pkgs])
            else:
                edit = set()
                if mod.dev_mode:
                    edit.add(mod.mid)

                if not mod.dev_mode and latest_ins == new_rel.version:
                    # Only metadata changed
                    tasks.run_task(tasks.RewriteModMetadata([mod]))
                else:
                    # NOTE: If a dev mod received a metadata update, we have an edge case in which this function doesn't
                    # do anything.
                    # * RewriteModMetadata would remove all local changes which is highly undesirable.
                    # * InstallTask doesn't update the metadata of installed mods (updates which change the version
                    #   number are technically new mods since they use a different folder)
                    tasks.run_task(tasks.InstallTask(sel_pkgs, new_rel, editable=edit))

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

        runner.run_mod(mod)
        return 0

    @QtCore.Slot(str, str, result=list)
    def getModTools(self, mid, spec):
        mod = self._get_mod(mid, spec)
        if mod in (-1, -2):
            return [mod]

        labels = set()
        try:
            for exe in mod.get_executables(user=True):
                if exe.get('label') is not None:
                    labels.add(exe['label'])
        except repo.NoExecutablesFound:
            pass

        labels = list(labels)
        labels.sort()
        return labels

    @QtCore.Slot(str, str, str, str, str, result=int)
    def runModTool(self, mid, spec, tool, tool_spec, label):
        mod = self._get_mod(mid, spec)
        if mod in (-1, -2):
            return mod

        if tool == '':
            tool = None
        else:
            tool = self._get_mod(tool, tool_spec)
            if tool in (-1, -2):
                return mod

        if label == '':
            label = None

        runner.run_mod(mod, tool, label)
        return 0

    @QtCore.Slot(str, str, str, bool, list)
    def runModAdvanced(self, mid, version, exe, is_tool, mod_flag):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return

        runner.run_mod_ex(mod, exe, mod_flag, is_tool)

    @QtCore.Slot(str, str, result=int)
    def vercmp(self, a, b):
        try:
            a = semantic_version.Version(a)
            b = semantic_version.Version(b)
        except Exception:
            # logging.exception('Someone passed an invalid version to vercmp()!')
            return 0

        return a.__cmp__(b)

    @QtCore.Slot(str)
    def openExternal(self, link):
        if ':\\' in link:
            link = QtCore.QUrl.fromLocalFile(link)
        else:
            link = QtCore.QUrl(link)

        QtGui.QDesktopServices.openUrl(link)

    @QtCore.Slot(str, str, result=str)
    def browseFolder(self, title, path):
        return QtWidgets.QFileDialog.getExistingDirectory(None, title, path)

    @QtCore.Slot(str, str, str, result=list)
    def browseFiles(self, title, path, filter_):
        res = QtWidgets.QFileDialog.getOpenFileNames(None, title, path, filter_)
        if res:
            return res[0]
        else:
            return []

    @QtCore.Slot(str, result=str)
    def verifyRootVPFolder(self, vp_path):
        vp_path_components = os.path.split(vp_path)
        if len(vp_path_components) != 2 or vp_path_components[1].lower() != 'root_fs2.vp':
            QtWidgets.QMessageBox.critical(
                None, 'Knossos', self.tr('The selected path is not to root_fs2.vp!'))
            return ''
        vp_dir = vp_path_components[0]
        if not util.is_fs2_retail_directory(vp_dir):
            QtWidgets.QMessageBox.critical(
                None, 'Knossos', self.tr('The selected root_fs2.vp\'s folder '
                                         'does not have the FreeSpace 2 files!'))
            return ''
        return vp_dir

    def _filter_out_hidden_files(self, files):
        if platform.system() != 'Windows':
            return [file for file in files if not file.startswith('.')]
        else: # TODO figure out how to identify hidden files on Windows
            return files

    def _is_program_files_path(self, path):
        prog_folders = [os.environ.get('ProgramFiles', 'C:/Program Files'),
                        os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')]
        prog_folders = tuple([f.lower().replace('\\', '/') for f in prog_folders])
        return path.lower().replace('\\', '/').startswith(prog_folders)

    @QtCore.Slot(str, result=bool)
    def setBasePath(self, path):
        if os.path.isfile(path):
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('The selected path is not a directory!'))
            return False
        if platform.system() == 'Windows':
            if self._is_program_files_path(path):
                result = QtWidgets.QMessageBox.question(None, 'Knossos',
                   self.tr('Using a folder in "Program Files" for the Knossos '
                           'library is not recommended, because you will have '
                           'to always run Knossos as Administrator. Use anyway?'))
                if result == QtWidgets.QMessageBox.No:
                    return False
        if os.path.isdir(path):
            if os.path.exists(os.path.join(path, center.get_library_json_name())):
                logging.info('Knossos library marker file found in selected path')
                # TODO log info from JSON file as debug messages?
            elif len(self._filter_out_hidden_files(os.listdir(path))) > 0:
                result = QtWidgets.QMessageBox.question(None, 'Knossos',
                    self.tr('Using a non-empty folder for the Knossos library '
                            'is not recommended, because it can cause problems'
                            ' for Knossos. Use anyway?'))
                if result == QtWidgets.QMessageBox.No:
                    return False
        if not os.path.lexists(path):
            result = QtWidgets.QMessageBox.question(None, 'Knossos',
                self.tr('The selected path does not exist. Should I create the folder?'))

            if result == QtWidgets.QMessageBox.Yes:
                try:
                    os.makedirs(path)
                except OSError:
                    QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr("Failed to create Knossos data folder!"))
                    return False
            else:
                return False
        else:
            vp_path = util.ipath(os.path.join(path, 'root_fs2.vp'))
            if os.path.isfile(vp_path):
                QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr("Please don't use an existing FS2 directory. It won't work! Select an empty directory instead."))
                return False

        center.settings['base_path'] = os.path.abspath(path)
        center.save_settings()
        util.ensure_tempdir()
        tasks.run_task(tasks.LoadLocalModsTask())
        return True

    # For when center.installed has not yet been initialized
    @QtCore.Slot(result=bool)
    def checkIfRetailInstalled(self):
        fs2_json_path = os.path.join(center.settings['base_path'], 'FS2', 'mod.json')
        return os.path.exists(fs2_json_path)

    @QtCore.Slot(int)
    def getSettings(self, cb_id):
        def cb():
            res = settings.get_settings()
            self.asyncCbFinished.emit(cb_id, json.dumps(res))

        Thread(target=cb).start()

    @QtCore.Slot(int)
    def getJoysticks(self, cb_id):
        def cb():
            res = settings.get_joysticks()
            self.asyncCbFinished.emit(cb_id, json.dumps(res))

        Thread(target=cb).start()

    @QtCore.Slot(str, str)
    def saveSetting(self, key, value):
        try:
            value = json.loads(value)
        except Exception:
            logging.exception('Failed to decode new value for setting "%s"! (%s)' % (key, value))
        else:
            settings.save_setting(key, value)

    @QtCore.Slot(str)
    def saveFsoSettings(self, data):
        try:
            data = json.loads(data)
        except Exception:
            logging.exception('Failed to decode new FSO settings! (%s)' % data)
        else:
            center.settings['joystick'] = {
                'guid': data.get('joystick_guid', None),
                'id': data.get('joystick_id', 99999)
            }
            center.save_settings()

            settings.save_fso_settings(data)

    @QtCore.Slot(result=str)
    def getDefaultFsoCaps(self):
        flags = None

        if center.settings['fs2_bin']:
            try:
                flags = settings.get_fso_flags(center.settings['fs2_bin'])
            except Exception:
                logging.exception('Failed to fetch FSO flags!')

        try:
            return json.dumps(flags)
        except Exception:
            logging.exception('Failed to encode FSO flags!')

    @QtCore.Slot(result=str)
    def searchRetailData(self):
        # Huge thanks go to jr2 for discovering everything implemented here to detect possible FS2 retail installs.
        # --ngld

        folders = [r'C:\GOG Games\Freespace2', r'C:\Games\Freespace2', r'C:\Games\Freespace 2']

        reg = QtCore.QSettings(r'HKEY_CURRENT_USER\Software\Valve\Steam', QtCore.QSettings.NativeFormat)
        reg.setFallbacksEnabled(False)

        steam_path = reg.value('SteamPath')

        if not steam_path:
            logging.info('No SteamPath detected!')
        else:
            steam_config = os.path.join(steam_path, 'config/config.vdf')
            if not os.path.isfile(steam_config):
                logging.warning('config.vdf is not where I expected it!')
            else:
                folders.append(os.path.join(steam_path, 'steamapps', 'common', 'Freespace 2'))

                with open(steam_config, 'r') as stream:
                    for m in re.finditer(r'"BaseInstallFolder_[0-9]+"\s+"([^"]+)"', stream.read()):
                        folders.append(os.path.join(m.group(1), 'Freespace 2'))

        for path in (r'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\GOG.com\GOGFREESPACE2', r'HKEY_LOCAL_MACHINE\SOFTWARE\GOG.com\GOGFREESPACE2'):
            reg = QtCore.QSettings(path, QtCore.QSettings.NativeFormat)
            reg.setFallbacksEnabled(False)
            gog_path = reg.value('PATH')

            if gog_path:
                folders.append(gog_path)

        gog_db = os.path.expandvars(r'%ProgramData%\GOG.com\Galaxy\storage\index.db')
        if os.path.isfile(gog_db):
            try:
                db = sqlite3.connect(gog_db)
                c = db.cursor()
                c.execute('SELECT localpath FROM Products WHERE productId = 5')
                row = c.fetchone()
                if row:
                    folders.append(row[0])
            except Exception:
                logging.exception('Failed to read GOG index.db!')

        gog_db = os.path.expandvars(r'%ProgramData%\GOG.com\Galaxy\storage\galaxy.db')
        if os.path.isfile(gog_db):
            try:
                db = sqlite3.connect(gog_db)
                c = db.cursor()
                c.execute('SELECT installationPath FROM InstalledBaseProducts WHERE productId = 5')
                row = c.fetchone()
                if row:
                    folders.append(row[0])
            except Exception:
                logging.exception('Failed to read GOG galaxy.db!')

        for path in folders:
            if util.is_fs2_retail_directory(path):
                return path

        return ''

    @QtCore.Slot(str, result=bool)
    def copyRetailData(self, path):
        if util.is_fs2_retail_directory(path):
            tasks.run_task(tasks.GOGCopyTask(path, os.path.join(center.settings['base_path'], 'FS2')))
            return True
        elif os.path.isfile(path) and path.endswith('.exe'):
            tasks.run_task(tasks.GOGExtractTask(path, os.path.join(center.settings['base_path'], 'FS2')))
            return True
        elif os.path.isfile(path):
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('The selected path is not a directory and not an installer!'))
            return False
        else:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('The selected path does not contain the retail files!'))
            return False

    @QtCore.Slot(result=str)
    def getRunningTasks(self):
        tasks = center.main_win.get_tasks()
        res = {}

        for t, task in tasks.items():
            res[t] = {
                'title': task.title,
                'mods': [m.get() for m in task.mods]
            }

        try:
            return json.dumps(res)
        except Exception:
            logging.exception('Failed to encoding running tasks!')
            return 'null'

    @QtCore.Slot(str, str, str, str, str, str, result=bool)
    def createMod(self, ini_path, name, mid, version, mtype, parent):
        if mtype in ('mod', 'ext'):
            if parent != 'FS2':
                parent = self._get_mod(parent)

                if parent == -1:
                    QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('The selected parent TC is not valid!'))
                    return False
                else:
                    parent = parent.mid
        else:
            parent = None

        mod = repo.InstalledMod({
            'title': name,
            'id': mid,
            'version': version,
            'type': mtype,
            'parent': parent,
            'dev_mode': True
        })
        mod.generate_folder()

        if os.path.isdir(mod.folder):
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('There already exists a mod with the chosen ID!'))
            return False

        exists = False
        try:
            neb = nebula.NebulaClient()
            neb.login()
            exists = not neb.check_mod_id(mid, name)
        except nebula.InvalidLoginException:
            QtWidgets.QMessageBox.warning(None, 'Knossos',
                self.tr("Knossos couldn't check if your mod ID is unique because it couldn't connect to the Nebula. " +
                    "Continue at your own risk if you're sure it is unique, otherwise please abort."))
        except Exception:
            logging.exception('Failed to contact the nebula!')
            QtWidgets.QMessageBox.warning(None, 'Knossos',
                self.tr("Knossos couldn't check if your mod ID is unique because it couldn't connect to the Nebula. " +
                    "Continue at your own risk if you're sure it is unique, otherwise please abort."))

        if exists:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr('Your chosen mod ID is already being used by someone else. Please choose a different one.'))
            return False

        upper_folder = os.path.dirname(mod.folder)
        if not os.path.isdir(upper_folder):
            if mod.mtype in ('tool', 'engine') and upper_folder.endswith('bin'):
                try:
                    os.mkdir(upper_folder)
                except Exception:
                    logging.exception('Failed to create binary folder! (%s)' % upper_folder)
                    QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('I could not create the folder for binaries!'))
                    return False
            elif mod.mtype == 'tc':
                try:
                    os.mkdir(upper_folder)
                except Exception:
                    logging.exception('Failed to create TC folder! (%s)' % upper_folder)
                    QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('I could not create the folder for the TC!'))
                    return False
            else:
                logging.error('%s did not exist during mod creation! (parent = %s)' % (mod.folder, mod.parent))
                QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('The chosen parent does not exist! Something went very wrong here!!'))
                return False

        os.mkdir(mod.folder)

        if ini_path != '':
            # We need the ini mod for determining where to pull the VPs from
            ini_mod = repo.IniMod()
            ini_mod.load(ini_path)

            if len(ini_mod.get_primary_list()) > 0:
                QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr(
                    'Ini mods with a primary list are currently not supported for importing!'))
                return False

            # This dict will convert a known secondary list entry to a mod.json style dependency
            dependency_mapping = {
                "mediavps_2014": {
                    "id": "MVPS",
                    "version": "3.7.2",
                },
                "mediavps_3612": {
                    "id": "MVPS",
                    "version": "3.6.12",
                },
                "mediavps": {
                    "id": "MVPS",
                    "version": "3.6.10",
                },
            }

            package_dependencies = []

            for dependency in ini_mod.get_secondary_list():
                dependency = dependency.lower()  # The mapping only works for lower case
                if dependency not in dependency_mapping:
                    # An unknown dependency is just skipped
                    QtWidgets.QMessageBox.warning(None, 'Knossos',
                                                  self.tr(
                                                      'The mod.ini dependency %s is not known to Knossos and could not be converted to a mod.json dependency.')
                                                  % (dependency))
                    continue

                package_dependencies.append(dependency_mapping[dependency])

            task = tasks.VpExtractionTask(mod, ini_mod)

            def finish_import():
                for vp_file in task.get_results():
                    base_filename = os.path.basename(vp_file).replace(".vp", "")

                    pkg = repo.InstalledPackage({
                        'name': base_filename,
                        'status': 'required',
                        'folder': base_filename,
                        'dependencies': package_dependencies,
                        'is_vp': True
                    })
                    mod.add_pkg(pkg)

                center.installed.add_mod(mod)
                mod.update_mod_flag()
                try:
                    mod.save()
                except Exception:
                    QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save mod.json!'))
                    return

                center.main_win.update_mod_list()

            task.done.connect(finish_import)
            tasks.run_task(task)

            return True
        else:
            try:
                mod.save()
            except Exception:
                QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save mod.json!'))
                return False

            center.installed.add_mod(mod)
            center.main_win.update_mod_list()

            return True

    @QtCore.Slot(str, str, str, str, result=int)
    def addPackage(self, mid, version, pkg_name, pkg_folder):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return mod

        if not mod.dev_mode:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr("You can't edit \"%s\" because it isn't in dev mode!") % mod.title)
            return -1

        pkg = mod.add_pkg(repo.Package({'name': pkg_name}))
        pkg.folder = pkg_folder

        pkg_path = os.path.join(mod.folder, pkg_folder)
        if not os.path.isdir(pkg_path):
            os.mkdir(pkg_path)

        try:
            mod.save()
        except Exception:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save mod.json!'))
            return
        center.main_win.update_mod_list()

        return len(mod.packages) - 1

    @QtCore.Slot(str, str, int, result=bool)
    def deletePackage(self, mid, version, idx):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return False

        if idx < 0 or idx >= len(mod.packages):
            logging.error('Invalid index passed to deletePackage()!')
            return False

        if not mod.dev_mode:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr("You can't edit \"%s\" because it isn't in dev mode!") % mod.title)
            return False

        # TODO: Delete the package folder?
        del mod.packages[idx]
        try:
            mod.save()
        except Exception:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save mod.json!'))
            return False
        center.main_win.update_mod_list()

        return True

    @QtCore.Slot(str, result=str)
    def selectImage(self, old_path):
        if old_path == '':
            old_dir = None
        else:
            old_dir = os.path.dirname(old_path)

        new_path, used_filter = QtWidgets.QFileDialog.getOpenFileName(None, self.tr('Please select an image'), old_dir,
                                                                      self.tr('Image (*.png *.jpg *.jpeg *.gif *.bmp)'))

        if new_path:
            return new_path
        elif os.path.isfile(old_path):
            return old_path
        else:
            return ''

    @QtCore.Slot(str, result=list)
    def addPkgExe(self, folder):
        if sys.platform == 'win32':
            filter_ = self.tr('Executables (*.exe)')
        else:
            filter_ = '*'

        res = QtWidgets.QFileDialog.getOpenFileNames(None, self.tr('Please select one or more executables'),
            folder, filter_)

        if not res:
            return []
        else:
            return [os.path.relpath(item, folder) for item in res[0]]

    @QtCore.Slot(str, result=list)
    def findPkgExes(self, folder):
        result = []

        for path, dirs, files in os.walk(folder):
            for fn in files:
                fn = os.path.join(path, fn)

                if fn.endswith('.exe'):
                    result.append(fn)
                elif '.so' not in fn and os.stat(fn).st_mode & stat.S_IXUSR == stat.S_IXUSR:
                    result.append(fn)

        return [os.path.relpath(item, folder) for item in result]

    def _store_mod_images(self, mod, img, imlist):
        if isinstance(img, list):
            for i, item in enumerate(img):
                img[i] = self._store_mod_images(mod, item, imlist)

            return img

        path = os.path.join(mod.folder, 'kn_images')
        if not os.path.isdir(path):
            os.mkdir(path)

        if os.path.abspath(img).startswith(path):
            imlist.add(os.path.basename(img))
            return img

        name, ext = os.path.splitext(img)
        dest = os.path.join(path, util.gen_hash(img)[1] + ext)

        logging.debug('Copying image from %s to %s.', img, dest)
        shutil.copyfile(img, dest)

        imlist.add(os.path.basename(dest))
        return dest

    def _clean_mod_images(self, mod, images):
        path = os.path.join(mod.folder, 'kn_images')
        if not os.path.isdir(path):
            return

        for item in os.listdir(path):
            if item not in images:
                logging.debug('Removing %s from %s because it is no longer needed.', item, mod)
                os.unlink(os.path.join(path, item))

    @QtCore.Slot(str, result=bool)
    def saveModDetails(self, data):
        try:
            data = json.loads(data)
        except Exception:
            logging.exception('Failed to decode mod details!')
            QtWidgets.QMessageBox.critical(None, 'Error', self.tr('Internal data inconsistency. Please try again.'))
            return False

        mod = self._get_mod(data['id'], data['version'])
        if mod == -1:
            logging.error('Failed find mod "%s" during save!' % data['id'])
            QtWidgets.QMessageBox.critical(None, 'Error', self.tr('Failed to find the mod! Weird...'))
            return False

        if not mod.dev_mode:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr("You can't edit \"%s\" because it isn't in dev mode!") % mod.title)
            return False

        if mod.mtype == 'engine':
            mod.stability = data['stability']

        mod.title = data['title']
        mod.description = data['description']
        imlist = set()
        for prop in ('logo', 'tile', 'banner', 'screenshots', 'attachments'):
            if data[prop]:
                setattr(mod, prop, self._store_mod_images(mod, data[prop], imlist))
            elif isinstance(data[prop], list):
                setattr(mod, prop, [])
            else:
                setattr(mod, prop, None)

        self._clean_mod_images(mod, imlist)

        mod.release_thread = data['release_thread']
        mod.videos = []
        for line in data['video_urls'].split('\n'):
            line = line.strip()
            if line != '':
                mod.videos.append(line)

        if data['first_release']:
            try:
                mod.first_release = datetime.strptime(data['first_release'], '%Y-%m-%d')
            except ValueError:
                QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('The entered first release date is invalid!'))
                return False

        if data['last_update']:
            try:
                mod.last_update = datetime.strptime(data['last_update'], '%Y-%m-%d')
            except ValueError:
                QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('The entered last update date is invalid!'))
                return False

        try:
            mod.save()
        except Exception:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save mod.json!'))
            return False

        center.main_win.update_mod_list()
        return True

    @QtCore.Slot(str, str, str, str, result=bool)
    def savePackage(self, mid, version, pkg_name, data):
        try:
            data = json.loads(data)
        except Exception:
            logging.exception('Failed to decode mod details!')
            QtWidgets.QMessageBox.critical(None, 'Error', self.tr('Internal data inconsistency. Please try again.'))
            return False

        mod = self._get_mod(mid, version)
        if mod == -1:
            logging.error('Failed find mod "%s" during save!' % mid)
            QtWidgets.QMessageBox.critical(None, 'Error', self.tr('Failed to find the mod! Weird...'))
            return False

        if not mod.dev_mode:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr("You can't edit \"%s\" because it isn't in dev mode!") % mod.title)
            return False

        pkg = None
        for item in mod.packages:
            if item.name == pkg_name:
                pkg = item
                break

        if not pkg:
            logging.error('Failed to find package "%s" for mod "%s"!' % (pkg_name, mid))
            QtWidgets.QMessageBox.critical(None, 'Error', self.tr('Failed to find the package! Weird...'))
            return False

        pkg.notes = data['notes']
        pkg.status = data['status']
        pkg.dependencies = data['dependencies']

        if mod.mtype in ('engine', 'tool'):
            pkg.is_vp = False
            pkg.environment = data['environment']
            pkg.executables = data['executables']
        else:
            pkg.is_vp = data['is_vp']
            pkg.environment = None
            pkg.executables = []

        # Normalize
        pkg.set(pkg.get())
        mod.update_mod_flag()
        try:
            mod.save()
        except Exception:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save mod.json!'))
            return False

        center.main_win.update_mod_list()

        return True

    @QtCore.Slot(str, str, str, str, result=bool)
    def saveModFsoDetails(self, mid, version, build, cmdline):
        mod = self._get_mod(mid, version)
        if mod == -1:
            logging.error('Failed find mod "%s" during save!' % mid)
            QtWidgets.QMessageBox.critical(None, 'Error', self.tr('Failed to find the mod! Weird...'))
            return False

        if not mod.dev_mode:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr("You can't edit \"%s\" because it isn't in dev mode!") % mod.title)
            return False

        build = build.split('#')
        if len(build) != 2:
            logging.error('saveModFsoDetails(): build is not correctly formatted! (%s)' % build)
        else:
            if build[0] == 'custom':
                mod.custom_build = build[1]
            else:
                mod.custom_build = None

                try:
                    exes = mod.get_executables()
                except repo.NoExecutablesFound:
                    # Remove all dependencies on engines first to make sure that we don't create conflicting dependencies
                    for pkg in mod.packages:
                        for i, dep in reversed(list(enumerate(pkg.dependencies))):
                            try:
                                d = center.installed.query(dep['id'], dep['version'])
                            except repo.ModNotFound:
                                # This dependency isn't installed which shouldn't happen since it'll also cause problems
                                # elsewhere. However, we want to avoid removing a valid dependency just because of a user
                                # mistake so let's check if the dependency is still available.

                                try:
                                    d = center.mods.query(dep['id'], dep['version'])
                                except repo.ModNotFound:
                                    # Still not found. Assume that this dependency doesn't exist anymore and remove it to be safe.
                                    del pkg.dependencies[i]
                                    continue

                            if d.mtype == 'engine':
                                del pkg.dependencies[i]

                    done = False
                    for pkg in mod.packages:
                        if pkg.status == 'required':
                            pkg.dependencies.append({
                                'id': build[0],
                                'version': '>=' + build[1]
                            })
                            done = True
                            break

                    if not done:
                        QtWidgets.QMessageBox.critical(None, 'Error',
                            self.tr('Failed to save the selected FSO build. Make sure that you have at least one required' +
                            ' package!'))
                        return False
                else:
                    old_build = exes[0]['mod']
                    done = False

                    for pkg in mod.packages:
                        for dep in pkg.dependencies:
                            if dep['id'] == old_build.mid:
                                dep['id'] = build[0]
                                dep['version'] = '>=' + build[1]
                                done = True
                                break

                        if done:
                            break

                    if not done:
                        logging.error('Failed to update build dependency for "%s"! WHY?!?! (old_build = %s, new_build = %s)'
                            % (mod, old_build, build[0]))

        mod.cmdline = cmdline
        try:
            mod.save()
        except Exception:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save mod.json!'))
            return False

        center.main_win.update_mod_list()
        return True

    @QtCore.Slot(str, str, str, str)
    def saveUserFsoDetails(self, mid, version, build, cmdline):
        mod = self._get_mod(mid, version)
        if mod == -1:
            logging.error('Failed find mod "%s" during save!' % mid)
            QtWidgets.QMessageBox.critical(None, 'Error', self.tr('Failed to find the mod! Weird...'))
            return

        if build == '':
            mod.user_custom_build = None
            mod.user_exe = None
        else:
            build = build.split('#')
            if len(build) != 2:
                logging.error('saveModFsoDetails(): build is not correctly formatted! (%s)' % build)
            else:
                if build[0] == 'custom':
                    mod.user_custom_build = build[1]
                    mod.user_exe = None
                else:
                    mod.user_custom_build = None
                    mod.user_exe = build

        if cmdline == '#DEFAULT#':
            cmdline = None

        mod.user_cmdline = cmdline
        try:
            mod.save_user()
        except Exception:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save user.json!'))
            return

        center.main_win.update_mod_list()

    @QtCore.Slot(str, str, list, result=bool)
    def saveModFlag(self, mid, version, mod_flag):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return False

        mod.mod_flag = mod_flag
        try:
            mod.save()
        except Exception:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save mod.json!'))
            return False

        center.main_win.update_mod_list()
        return True

    @QtCore.Slot(str, str, bool)
    def startUpload(self, mid, version, private):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return

        self._last_upload = tasks.run_task(tasks.UploadTask(mod, private))

    @QtCore.Slot()
    def cancelUpload(self):
        if self._last_upload:
            self._last_upload.abort()
            self._last_upload = None

    @QtCore.Slot(str, str, result=bool)
    def nebLogin(self, user, password):
        client = nebula.NebulaClient()
        try:
            result = client.login(user, password)
        except Exception:
            result = False
            logging.exception('Failed to login to Nebula!')

        if result:
            QtWidgets.QMessageBox.information(None, 'Knossos', 'Login successful!')

            # TODO: Figure out a better way for this!
            center.settings['neb_user'] = user
            center.settings['neb_password'] = password
            center.save_settings()

            return True
        else:
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'Login failed.')

    @QtCore.Slot(result=bool)
    def nebLogout(self):
        center.settings['neb_user'] = ''
        center.settings['neb_password'] = ''
        center.save_settings()

        return True

    @QtCore.Slot(str, str, str)
    def nebRegister(self, user, password, email):
        client = nebula.NebulaClient()

        try:
            result = client.register(user, password, email)
        except Exception:
            result = False
            logging.exception('Failed to register to the Nebula!')

        if result:
            QtWidgets.QMessageBox.information(None, 'Knossos',
                'Registered. Please check your e-mail inbox for your confirmation mail.')
        else:
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'Registration failed. Please contact ngld.')

    @QtCore.Slot(str)
    def nebResetPassword(self, user):
        client = nebula.NebulaClient()

        try:
            result = client.reset_password(user)
        except Exception:
            result = False
            logging.exception('Failed to reset Nebula password!')

        if result:
            QtWidgets.QMessageBox.information(None, 'Knossos', 'You should now receive a mail with a reset link. ' +
                'Remember to check your spam folder!')
        else:
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'Request failed. Please contect ngld.')

    @QtCore.Slot(str, str, str, result=bool)
    def nebReportMod(self, mid, version, message):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return False

        client = nebula.NebulaClient()
        try:
            client.report_release(mod, message)
        except Exception:
            logging.exception('Failed to send mod report!')
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'Request failed. Please contect ngld.')
            return False
        else:
            QtWidgets.QMessageBox.information(None, 'Knossos',
                'Thanks for your report. We will act on it as soon as possible.')
            return True

    @QtCore.Slot(str, str)
    def nebDeleteMod(self, mid, version):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return

        fine = False
        client = nebula.NebulaClient()
        try:
            client.delete_release(mod)
            fine = True
        except nebula.AccessDeniedException:
            QtWidgets.QMessageBox.critical(None, 'Knossos', "You can't do that!")
        except nebula.InvalidLoginException:
            QtWidgets.QMessageBox.critical(None, 'Knossos', "You can't delete this mod from the nebula until you login.")
        except nebula.RequestFailedException as exc:
            if exc.args[0] == 'not found':
                QtWidgets.QMessageBox.information(None, 'Knossos',
                    "This mod hasn't been uploaded and thus can't be removed from the nebula.")
                fine = True
            else:
                QtWidgets.QMessageBox.critical(None, 'Knossos', 'Request failed. Please contect ngld.')
        except Exception:
            logging.exception('Failed to send mod report!')
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                'Request failed. You might have problems connecting to fsnebula.org.')
        else:
            QtWidgets.QMessageBox.information(None, 'Knossos', 'The release was successfully deleted.')

        if fine:
            result = QtWidgets.QMessageBox.question(None, 'Knossos', 'Should the local files be deleted?')
            if result == QtWidgets.QMessageBox.Yes:
                tasks.run_task(tasks.RemoveModFolder(mod))

    @QtCore.Slot(str, str)
    def removeModFolder(self, mid, version):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return

        tasks.run_task(tasks.RemoveModFolder(mod))

    @QtCore.Slot(result=str)
    def selectCustomBuild(self):
        if sys.platform == 'win32':
            filter_ = '*.exe'
        else:
            filter_ = '*'

        res = QtWidgets.QFileDialog.getOpenFileNames(None, 'Please select your FSO build', None, filter_)
        if res and len(res[0]) > 0:
            return res[0][0]
        else:
            return ''

    @QtCore.Slot(str, str, result=str)
    def getFsoBuild(self, mid, version):
        mod = self._get_mod(mid, version)

        if mod.custom_build:
            return 'custom#' + mod.custom_build

        try:
            for item in mod.get_executables():
                if item.get('label') is None:
                    mod = item['mod']
                    return mod.mid + '#' + str(mod.version)
        except repo.NoExecutablesFound:
            return ''
        except Exception:
            logging.exception('Failed to fetch executables!')

        return ''

    @QtCore.Slot(str, str, result=str)
    def getUserBuild(self, mid, version):
        mod = self._get_mod(mid, version)
        if not isinstance(mod, repo.Mod):
            return ''

        if mod.user_custom_build:
            return 'custom#' + mod.user_custom_build

        try:
            for item in mod.get_executables(user=True):
                if item.get('label') is None:
                    mod = item['mod']
                    return mod.mid + '#' + str(mod.version)
        except repo.NoExecutablesFound:
            return ''
        except Exception:
            logging.exception('Failed to fetch executables!')

        return ''

    @QtCore.Slot(str, str, int)
    def getFsoCaps(self, mid, version, cb_id):
        mod = None
        if mid != 'custom':
            mod = self._get_mod(mid, version)
            if mod in (-1, -2):
                return

        def helper():
            flags = None
            exes = []
            if not mod:
                flags = settings.get_fso_flags(version)
            else:
                try:
                    for exe in mod.get_executables():
                        if not exe.get('label'):
                            if not flags:
                                flags = settings.get_fso_flags(exe['file'])

                            exes.append(os.path.basename(exe['file']))
                except repo.NoExecutablesFound:
                    pass
                except Exception:
                    logging.exception('Failed to fetch FSO flags!')

            try:
                self.asyncCbFinished.emit(cb_id, json.dumps({
                    'flags': flags,
                    'exes': exes
                }))
            except Exception:
                logging.exception('Failed to encode FSO flags!')

        Thread(target=helper).start()

    @QtCore.Slot(str, str, str, str, result=bool)
    def createModVersion(self, mid, version, dest_ver, method):
        mod = self._get_mod(mid, version)

        if not isinstance(mod, repo.InstalledMod):
            logging.error('Mod %s (%s) should have gotten a new version but was not found!' % (mid, version))

            QtWidgets.QMessageBox.critical(None, self.tr('Error'),
                self.tr("Somehow I lost the mod you're talking about! I'm sorry, this is a bug."))
            return False

        if not mod.dev_mode:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr("You can't edit \"%s\" because it isn't in dev mode!") % mod.title)
            return False

        old_ver = semantic_version.Version(version, partial=True)
        try:
            dest_ver = semantic_version.Version(dest_ver, partial=True)
        except ValueError:
            QtWidgets.QMessageBox.critical(None, self.tr('Error'),
                self.tr("The specified version number is invalid!"))
            return False
        except Exception:
            logging.exception('Failed to parse new version (%s)!' % dest_ver)
            QtWidgets.QMessageBox.critical(None, self.tr('Error'),
                self.tr("Failed to parse the new version! This is a bug."))
            return False

        if old_ver >= dest_ver:
            # TODO: Is this check too restrictive?
            QtWidgets.QMessageBox.critical(None, self.tr('Error'),
                self.tr("The new version has to be higher than the old version!"))
            return False

        new_mod = mod.copy()
        new_mod.version = dest_ver
        new_mod.generate_folder()

        if os.path.isdir(new_mod.folder):
            QtWidgets.QMessageBox.critical(None, self.tr('Error'),
                self.tr("The destination folder (%s) already exists! I won't overwrite an existing folder!") % new_mod.folder)
            return False

        if method == 'copy':
            os.mkdir(new_mod.folder)

            tasks.run_task(tasks.CopyFolderTask(mod.folder, new_mod.folder))
        elif method == 'rename':
            try:
                util.safe_rename(mod.folder, new_mod.folder)
            except OSError:
                logging.exception('Failed to rename mod folder for new version!')
                QtWidgets.QMessageBox.critical(None, self.tr('Error'),
                    self.tr('Failed to rename folder "%s"! Make sure that no other program has locked it.') % mod.folder)
                return False

            try:
                center.installed.remove_mod(mod)
            except repo.ModNotFound:
                logging.exception('The old mod is missing after rename! Did the copy fail?')
        elif method == 'empty':
            os.mkdir(new_mod.folder)

            for pkg in new_mod.packages:
                os.mkdir(os.path.join(new_mod.folder, pkg.folder))

        try:
            new_mod.save()
        except Exception:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save mod.json!'))
            return False

        center.installed.add_mod(new_mod)
        center.main_win.update_mod_list()

        return True

    @QtCore.Slot(int, int, str)
    def testVoice(self, voice, volume, text):
        Thread(target=clibs.speak, args=(voice, volume, text)).start()

    @QtCore.Slot(str)
    def showDescEditor(self, text):
        windows.DescriptionEditorWindow(text)

    @QtCore.Slot(str, result=str)
    def parseIniMod(self, path):
        mod = repo.IniMod()
        mod.load(path)
        return json.dumps(mod.get())

    @QtCore.Slot(str, str)
    def verifyModIntegrity(self, mid, version):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return

        tasks.run_task(tasks.CheckFilesTask(mod.packages, mod))

    @QtCore.Slot()
    def openScreenshotFolder(self):
        path = os.path.join(settings.get_fso_profile_path(), 'screenshots')

        if os.path.isdir(path):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))
        else:
            QtWidgets.QMessageBox.critical(None, 'Knossos', "The screenshot folder doesn't exist. Try taking screenshots before clicking this button!")

    @QtCore.Slot(result=str)
    def getDefaultBasePath(self):
        if sys.platform == 'win32':
            return 'C:\\Games\\FreespaceOpen'
        elif sys.platform == 'linux':
            return os.path.expanduser('~/games/FreespaceOpen')
        elif sys.platform == 'darwin':
            return os.path.expanduser('~/Documents/Games/FreespaceOpen')
        else:
            return ''

    @QtCore.Slot()
    def openFsoDebugLog(self):
        logpath = os.path.join(settings.get_fso_profile_path(), 'data/fs2_open.log')
        if not os.path.isfile(logpath):
            QtWidgets.QMessageBox.warning(None, 'Knossos',
                'Sorry, but I can\'t find the fs2_open.log file.\nDid you run the debug build?')
            return

        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(logpath))

    @QtCore.Slot(result=str)
    def uploadFsoDebugLog(self):
        try:
            logpath = os.path.join(settings.get_fso_profile_path(), 'data/fs2_open.log')
            if not os.path.isfile(logpath):
                QtWidgets.QMessageBox.warning(None, 'Knossos',
                    'Sorry, but I can\'t find the fs2_open.log file.\nDid you run the debug build?')
                return ''

            st = os.stat(logpath)
            if st.st_size > 5 * (1024 ** 2):
                QtWidgets.QMessageBox.critical(None, 'Knossos',
                    "Your log is larger than 5 MB! I unfortunately can't upload logs that big.")
                return ''

            # Date check
            changed_at = datetime.fromtimestamp(st.st_mtime)
            age = datetime.now() - changed_at

            message = 'The most recent log was generated '

            if age.days == 0:
                message += 'today'
            elif age.days == 1:
                message += 'yesterday'
            else:
                message += '%d days ago' % age.days

            message += changed_at.strftime(' at %X')
            message += '. Is this when you encountered a problem?'

            box = QtWidgets.QMessageBox()
            box.setIcon(QtWidgets.QMessageBox.Question)
            box.setText(message)
            box.setWindowTitle('Knossos')

            box.addButton('Yes, upload', QtWidgets.QMessageBox.YesRole)
            # no_again = box.addButton('No, run again and generate a new log', QtWidgets.QMessageBox.NoRole)
            no_abort = box.addButton('No', QtWidgets.QMessageBox.RejectRole)
            box.exec_()

            if box.clickedButton() == no_abort:
                return

            client = nebula.NebulaClient()
            with open(logpath, 'r') as stream:
                log_link = client.upload_log(stream.read())
        except nebula.InvalidLoginException:
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'You have to login to upload logs!')
        except Exception:
            logging.exception('Log upload failed!')
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                'The log upload failed for an unknown reason! Please make sure your internet connection is fine.')
        else:
            if log_link:
                return log_link
            else:
                QtWidgets.QMessageBox.critical(None, 'Knossos', 'The log upload failed for an unknown reason!')

        return ''

    @QtCore.Slot()
    def openKnossosLog(self):
        from .launcher import log_path

        if not os.path.isfile(log_path):
            QtWidgets.QMessageBox.warning(None, 'Knossos',
                'Sorry, but I can\'t find the Knossos log. Something went *really* wrong.')
            return

        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(log_path))

    @QtCore.Slot(result=str)
    def uploadKnossosLog(self):
        log_link = None

        try:
            from .launcher import log_path

            if not os.path.isfile(log_path):
                QtWidgets.QMessageBox.warning(None, 'Knossos',
                    'Sorry, but I can\'t find the Knossos log. Something went *really* wrong.')
                return ''

            st = os.stat(log_path)
            if st.st_size > 5 * (1024 ** 2):
                QtWidgets.QMessageBox.critical(None, 'Knossos',
                    "Your log is larger than 5 MB! I unfortunately can't upload logs that big.")
                return ''

            client = nebula.NebulaClient()
            with open(log_path, 'r') as stream:
                log_link = client.upload_log(stream.read())

        except nebula.InvalidLoginException:
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'You have to login to upload logs!')
        except Exception:
            logging.exception('Log upload failed!')
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                'The log upload failed for an unknown reason! Please make sure your internet connection is fine.')
        else:
            if log_link:
                return log_link
            else:
                QtWidgets.QMessageBox.critical(None, 'Knossos', 'The log upload failed for an unknown reason!')

        return ''

    @QtCore.Slot(str, result=str)
    def getGlobalFlags(self, build):
        return json.dumps(center.settings['fso_flags'].get(build, {}))

    @QtCore.Slot(str, str)
    def saveGlobalFlags(self, build, flags):
        try:
            center.settings['fso_flags'][build] = json.loads(flags)
        except Exception:
            logging.exception('Failed to decode flags from JS!')
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'Failed to decode flags!')
            return

        center.save_settings()
        QtWidgets.QMessageBox.information(None, 'Knossos', 'The settings have been successfully saved.')

    @QtCore.Slot(str, str)
    def applyGlobalFlagsToAll(self, flags, custom_flags):
        try:
            flags = json.loads(flags)
        except Exception:
            logging.exception('Failed to decode flags from JS!')
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'Failed to decode flags!')
            return

        engine_mods = []

        for mvs in center.installed.mods.values():
            if mvs[0].mtype == 'engine':
                engine_mods.extend(mvs)

        tasks.run_task(tasks.ApplyEngineFlagsTask(engine_mods, flags, custom_flags))

    @QtCore.Slot(str, str, result=str)
    def getModCmdline(self, mid, version):
        mod = self._get_mod(mid, version)
        if mod in (-1, -2):
            return ''

        try:
            return ' '.join(runner.apply_global_flags(mod))
        except repo.NoExecutablesFound:
            return ''

    @QtCore.Slot(result=str)
    def getEngineBuilds(self):
        builds = []
        for mvs in center.installed.mods.values():
            if mvs[0].mtype == 'engine':
                for mod in mvs:
                    builds.append(mod.get())

        return json.dumps(builds)

    @QtCore.Slot(str, int)
    def getTeamMembers(self, mid, cb_id):
        def helper():
            try:
                client = nebula.NebulaClient()
                members = client.get_team_members(mid)
            except nebula.InvalidLoginException:
                members = {'result': False, 'reason': 'no login'}
            except Exception:
                logging.exception('Failed to retrieve members!')
                members = {'result': False, 'reason': 'exception'}

            self.asyncCbFinished.emit(cb_id, json.dumps(members))

        Thread(target=helper).start()

    @QtCore.Slot(str, str, int)
    def updateTeamMembers(self, mid, members, cb_id):
        try:
            members = json.loads(members)
        except json.JSONDecodeError:
            logging.exception('Failed to decode members!')

            QtWidgets.QMessageBox.critical(None, 'Knossos', 'Failed to decode team members')
            self.asyncCbFinished.emit(cb_id, 'false')
            return

        def helper():
            try:
                client = nebula.NebulaClient()
                helper2(client.update_team_members(mid, members))
            except Exception:
                logging.exception('Failed to save team members!')
                helper2({
                    'result': False,
                    'reason': 'exception'
                })

        @run_in_qt
        def helper2(result):
            msg = None
            reason = result.get('reason', None)

            if result['result']:
                self.asyncCbFinished.emit(cb_id, 'true')
                return
            elif reason == 'owners_changed':
                msg = "Your changes weren't saved because you aren't permitted to modify the mod Owners!"
            elif reason == 'no_owners':
                msg = "Your changes couldn't be saved because you need to specify at least one Owner!"
            elif reason == 'member_not_found':
                msg = 'Your changes could not be saved because the user "%s" was not found.' % result['member']
            else:
                msg = "Your changes couldn't be saved because an unexpected error ocurred!"

            QtWidgets.QMessageBox.critical(None, 'Knossos', msg)
            self.asyncCbFinished.emit(cb_id, 'false')

        Thread(target=helper).start()

    @QtCore.Slot(str)
    def reportError(self, msg):
        logging.error('JS Error: %s' % msg)

    @QtCore.Slot()
    def fixBuildSelection(self):
        tasks.run_task(tasks.FixUserBuildSelectionTask())

    @QtCore.Slot(bool)
    def fixImages(self, do_devs):
        tasks.run_task(tasks.FixImagesTask(do_devs))

    @QtCore.Slot()
    def rewriteModJson(self):
        tasks.run_task(tasks.RewriteModMetadata(center.installed.get_list()))

    @QtCore.Slot()
    def showTempHelpPopup(self):
        QtWidgets.QMessageBox.information(None, 'Knossos',
                                          'The help system isn\'t implemented yet, but you '
                                          'can ask for help on the <a href="https://discord.gg/qfReB8t">#knossos</a> '
                                          'channel on Discord or on the '
                                          '<a href="https://www.hard-light.net/forums/index.php?topic=94068.0">'
                                          'Knossos release thread</a> on the Hard Light Productions forums.')

    @QtCore.Slot(str, result=str)
    def setSortType(self, sort_type):
        center.sort_type = sort_type
        center.main_win.update_mod_list()
        return sort_type


if QtWebChannel:
    BrowserCtrl = WebBridge
else:
    class BrowserCtrl(object):
        _view = None
        _nam = None
        bridge = None

        def __init__(self, webView):
            self._view = webView
            self.bridge = WebBridge()

            settings = webView.settings()
            settings.setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled, True)

            frame = webView.page().mainFrame()
            frame.javaScriptWindowObjectCleared.connect(self.insert_bridge)

        def load(self):
            link = 'qrc:///html/index.html'
            self._view.load(QtCore.QUrl(link))

        def insert_bridge(self):
            frame = self._view.page().mainFrame()

            del self.bridge
            self.bridge = WebBridge()
            frame.addToJavaScriptWindowObject('fs2mod', self.bridge)
