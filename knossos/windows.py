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

import os
import sys
import logging
import shlex
import functools
import json
import semantic_version

from . import uhf
uhf(__name__)

from . import center, util, integration, api, web, repo, launcher, runner
from .qt import QtCore, QtGui, QtWidgets, load_styles
from .ui.hell import Ui_MainWindow as Ui_Hell
from .ui.gogextract import Ui_Dialog as Ui_Gogextract
from .ui.add_repo import Ui_Dialog as Ui_AddRepo
from .ui.settings2 import Ui_Dialog as Ui_Settings
from .ui.settings_about import Ui_Form as Ui_Settings_About
from .ui.settings_sources import Ui_Form as Ui_Settings_Sources
from .ui.settings_versions import Ui_Form as Ui_Settings_Versions
from .ui.settings_knossos import Ui_Form as Ui_Settings_Knossos
from .ui.settings_fso import Ui_Form as Ui_Settings_Fso
from .ui.settings_video import Ui_Form as Ui_Settings_Video
from .ui.settings_audio import Ui_Form as Ui_Settings_Audio
from .ui.settings_input import Ui_Form as Ui_Settings_Input
from .ui.settings_network import Ui_Form as Ui_Settings_Network
from .ui.settings_help import Ui_Form as Ui_Settings_Help
from .ui.flags import Ui_Dialog as Ui_Flags
from .ui.install import Ui_Dialog as Ui_Install
from .ui.mod_settings import Ui_Dialog as Ui_Mod_Settings
from .ui.mod_versions import Ui_Dialog as Ui_Mod_Versions
from .ui.log_viewer import Ui_Dialog as Ui_Log_Viewer
from .tasks import run_task, GOGExtractTask, InstallTask, UninstallTask, WindowsUpdateTask, CheckTask, CheckFilesTask

# Keep references to all open windows to prevent the GC from deleting them.
_open_wins = []


class QDialog(QtWidgets.QDialog):

    def __init__(self, *args):
        super(QDialog, self).__init__(*args)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)


class QMainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args):
        super(QMainWindow, self).__init__(*args)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def closeEvent(self, e):
        e.accept()

        center.app.quit()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.ActivationChange and integration.current is not None:
            integration.current.annoy_user(False)

        return super(QMainWindow, self).changeEvent(event)


class Window(object):
    win = None
    closed = True
    _is_window = True
    _tpl_cache = None
    _styles = ''
    _qchildren = None

    def __init__(self, window=True):
        super(Window, self).__init__()

        self._is_window = window
        self._tpl_cache = {}
        self._qchildren = []

    def _create_win(self, ui_class, qt_widget=QDialog):
        if not self._is_window:
            qt_widget = QtWidgets.QWidget

        self.win = util.init_ui(ui_class(), qt_widget())

    def open(self):
        global _open_wins

        if not self.closed:
            return

        self.closed = False
        _open_wins.append(self)
        self.win.destroyed.connect(self._del)
        self.win.show()

    def close(self):
        self.win.close()

    def _del(self):
        global _open_wins

        if self.closed:
            return

        self.closed = True

        if self in _open_wins:
            _open_wins.remove(self)

    def label_tpl(self, label, **vars):
        name = label.objectName()
        if name in self._tpl_cache:
            text = self._tpl_cache[name]
        else:
            text = self._tpl_cache[name] = label.text()

        for name, value in vars.items():
            text = text.replace('{' + name + '}', value)

        label.setText(text)

    def load_styles(self, path, append=True):
        data = load_styles(path)

        if append:
            self._styles += data
        else:
            self._styles = data

        self.win.setStyleSheet(self._styles)


class HellWindow(Window):
    _tasks = None
    _mod_filter = 'installed'
    browser_ctrl = None
    progress_win = None

    def __init__(self, window=True):
        super(HellWindow, self).__init__(window)
        self._tasks = {}

        self._create_win(Ui_Hell, QMainWindow)
        self.browser_ctrl = web.BrowserCtrl(self.win.webView)

        self.win.backButton.clicked.connect(self.win.webView.back)
        self.win.searchEdit.textEdited.connect(self.search_mods)
        self.win.updateButton.clicked.connect(api.fetch_list)
        self.win.settingsButton.clicked.connect(self.show_settings)

        for button in ('installed', 'available', 'updates', 'progress'):
            bt = getattr(self.win, button + 'Button')
            hdl = functools.partial(self.update_mod_buttons, button)

            setattr(self, '_mod_button_hdl_' + button, hdl)
            bt.clicked.connect(hdl)

        self.win.webView.loadStarted.connect(self.show_indicator)
        self.win.webView.loadFinished.connect(self.check_loaded)

        center.signals.update_avail.connect(self.ask_update)
        center.signals.repo_updated.connect(self.check_new_repo)
        center.signals.task_launched.connect(self.watch_task)

        self.win.pageControls.hide()
        self.win.progressInfo.hide()
        self.open()

    def _del(self):
        center.signals.update_avail.disconnect(self.ask_update)
        center.signals.repo_updated.disconnect(self.check_new_repo)
        center.signals.task_launched.disconnect(self.watch_task)

        super(HellWindow, self)._del()

    def check_fso(self, interactive=True):
        if center.settings['fs2_path'] is not None:
            self.win.pageControls.setEnabled(True)
            self.win.updateButton.setEnabled(True)
            self.win.searchEdit.setEnabled(True)
            self.win.tabButtons.setEnabled(True)

            if interactive and self.win.webView.url().toString() == 'qrc:///html/welcome.html':
                self.update_mod_buttons('available')
        else:
            # Make sure the user has a complete configuration
            if not SettingsWindow.has_config():
                tmp = SettingsWindow()
                tmp.write_config()
                tmp.close()

            self.win.webView.load(QtCore.QUrl('qrc:///html/welcome.html'))
            self.win.pageControls.setEnabled(False)
            self.win.updateButton.setEnabled(False)
            self.win.searchEdit.setEnabled(False)
            self.win.tabButtons.setEnabled(False)

    def check_new_repo(self):
        updates = len(center.installed.get_updates())
        self.win.updatesButton.setText('Updates (%d)' % updates)

        self.update_mod_list()

    def ask_update(self, version):
        # We only have an updater for windows.
        if sys.platform.startswith('win'):
            msg = 'There\'s an update available!\nDo you want to install Knossos %s now?' % str(version)
            buttons = QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            result = QtWidgets.QMessageBox.question(center.app.activeWindow(), 'Knossos', msg, buttons)
            if result == QtWidgets.QMessageBox.Yes:
                run_task(WindowsUpdateTask())
        else:
            msg = 'There\'s an update available!\nYou should update to Knossos %s.' % str(version)
            QtWidgets.QMessageBox.information(center.app.activeWindow(), 'Knossos', msg)

    def update_repo_list(self):
        api.fetch_list()

    def search_mods(self):
        mods = None

        if self._mod_filter == 'installed':
            mods = center.installed.mods
        elif self._mod_filter == 'available':
            mods = {}
            for mid, mvs in center.mods.mods.items():
                if mid not in center.installed.mods:
                    mods[mid] = mvs
        elif self._mod_filter == 'updates':
            mods = {}
            for mid in center.installed.get_updates():
                mods[mid] = center.installed.mods[mid]
        elif self._mod_filter == 'progress':
            mods = {}

        # Now filter the mods.
        query = self.win.searchEdit.text().lower()
        result = {}
        for mid, mvs in mods.items():
            if query in mvs[0].title.lower():
                result[mid] = [mod.get() for mod in mvs]

        return result, self._mod_filter

    def update_mod_list(self):
        result, filter_ = self.search_mods()
        self.browser_ctrl.bridge.updateModlist.emit(result, filter_)

    def show_settings(self):
        SettingsWindow()

    def show_indicator(self):
        self.win.setCursor(QtCore.Qt.BusyCursor)

    def check_loaded(self, success):
        self.win.unsetCursor()

        page = self.win.webView.url().toString()
        if page == 'qrc:///html/modlist.html':
            self.win.listControls.show()
            self.win.pageControls.hide()

            # QtCore.QTimer.singleShot(30, lambda: self.update_mod_buttons(self._mod_filter))
        else:
            self.win.listControls.hide()
            self.win.pageControls.show()

    def update_mod_buttons(self, clicked=None):
        for button in ('installed', 'available', 'updates', 'progress'):
            getattr(self.win, button + 'Button').setChecked(button == clicked)

        self._mod_filter = clicked
        page = self.win.webView.url().toString()
        if page != 'qrc:///html/modlist.html':
            self.win.webView.load(QtCore.QUrl('qrc:///html/modlist.html'))
        else:
            self.update_mod_list()

    def watch_task(self, task):
        logging.debug('Task "%s" (%d, %s) started.', task.title, id(task), task.__class__)
        self._tasks[id(task)] = task
        self.browser_ctrl.bridge.taskStarted.emit(id(task), task.title)

        task.done.connect(functools.partial(self._forget_task, task))
        task.progress.connect(functools.partial(self._track_progress, task))

        if len(self._tasks) == 1:
            self.win.progressInfo.show()
            self.win.progressLabel.setText(task.title)
            self.win.progressBar.setValue(0)

            integration.current.show_progress(0)
        else:
            # TODO: Stop being lazy and calculate the aggregate progress.
            self.win.progressBar.hide()
            self.win.progressLabel.setText('Working...')

    def _track_progress(self, task, pi):
        subs = [item for item in pi[1].values()]
        self.browser_ctrl.bridge.taskProgress.emit(id(task), pi[0] * 100, json.dumps(subs), pi[2])

        if len(self._tasks) == 1:
            integration.current.set_progress(pi[0])
            self.win.progressBar.setValue(pi[0] * 100)

    def _forget_task(self, task):
        logging.debug('Task "%s" (%d) finished.', task.title, id(task))
        self.browser_ctrl.bridge.taskFinished.emit(id(task))
        del self._tasks[id(task)]

        if len(self._tasks) == 1:
            task = list(self._tasks.values())[0]
            self.win.progressLabel.setText(task.title)
            self.win.progressBar.setValue(task.get_progress()[0])
            self.win.progressBar.show()
        elif len(self._tasks) == 0:
            self.win.progressInfo.hide()
            integration.current.hide_progress()

    def abort_task(self, task):
        if task in self._tasks:
            self._tasks[task].abort()


# TODO: Move the settings read/write logic into another module.
class SettingsWindow(Window):
    _tabs = None
    _builds = None

    def __init__(self):
        self._tabs = {}
        self._create_win(Ui_Settings)

        self.win.treeWidget.expandAll()
        self.win.treeWidget.currentItemChanged.connect(self.select_tab)
        self.win.saveButton.clicked.connect(self.write_config)

        self._tabs['About Knossos'] = tab = util.init_ui(Ui_Settings_About(), QtWidgets.QWidget())

        self._tabs['Launcher settings'] = tab = util.init_ui(Ui_Settings_Knossos(), QtWidgets.QWidget())
        tab.versionLabel.setText(center.VERSION)
        tab.maxDownloads.setValue(center.settings['max_downloads'])

        if launcher.log_path is None:
            tab.debugLog.hide()
        else:
            tab.debugLog.clicked.connect(self.show_knossos_log)

        tab.clearHashes.clicked.connect(self.clear_hash_cache)

        if center.settings['update_channel'] == 'stable':
            tab.updateChannel.setCurrentIndex(0)
        else:
            tab.updateChannel.setCurrentIndex(1)

        if center.settings['update_notify']:
            tab.updateNotify.setCheckState(QtCore.Qt.Checked)
        else:
            tab.updateNotify.setCheckState(QtCore.Qt.Unchecked)

        if center.settings['use_raven']:
            tab.reportErrors.setCheckState(QtCore.Qt.Checked)
        else:
            tab.reportErrors.setCheckState(QtCore.Qt.Unchecked)

        tab.maxDownloads.valueChanged.connect(self.update_max_downloads)
        tab.updateChannel.currentIndexChanged.connect(self.save_update_settings)
        tab.updateNotify.stateChanged.connect(self.save_update_settings)
        tab.reportErrors.stateChanged.connect(self.save_report_settings)

        self._tabs['Retail install'] = tab = GogExtractWindow(False)
        tab.win.cancelButton.hide()

        self._tabs['Mod sources'] = tab = util.init_ui(Ui_Settings_Sources(), QtWidgets.QWidget())
        tab.addSource.clicked.connect(self.add_repo)
        tab.editSource.clicked.connect(self.edit_repo)
        tab.removeSource.clicked.connect(self.remove_repo)
        tab.sourceList.itemDoubleClicked.connect(self.edit_repo)

        self._tabs['Mod versions'] = tab = util.init_ui(Ui_Settings_Versions(), QtWidgets.QWidget())

        self._tabs['Game settings'] = tab = util.init_ui(Ui_Settings_Fso(), QtWidgets.QWidget())
        tab.browseButton.clicked.connect(self.select_fs2_path)
        tab.build.activated.connect(self.save_build)
        tab.openLog.clicked.connect(self.show_fso_log)

        self._tabs['Video'] = tab = util.init_ui(Ui_Settings_Video(), QtWidgets.QWidget())
        self._tabs['Audio'] = tab = util.init_ui(Ui_Settings_Audio(), QtWidgets.QWidget())
        self._tabs['Input'] = tab = util.init_ui(Ui_Settings_Input(), QtWidgets.QWidget())
        self._tabs['Network'] = tab = util.init_ui(Ui_Settings_Network(), QtWidgets.QWidget())

        self._tabs['Default flags'] = tab = FlagsWindow(window=False)
        if center.settings['fs2_path'] is None:
            tab.win.setEnabled(False)

        self._tabs['Help'] = util.init_ui(Ui_Settings_Help(), QtWidgets.QWidget())

        center.signals.fs2_path_changed.connect(self.read_config)
        center.signals.fs2_bin_changed.connect(tab.read_flags)

        self.update_repo_list()
        self.read_config()

        self.show_tab('About Knossos')
        self.open()

    def _del(self):
        center.signals.fs2_path_changed.disconnect(self.read_config)
        center.signals.fs2_bin_changed.disconnect(self._tabs['Default flags'].read_flags)

        super(SettingsWindow, self)._del()

    def show_tab(self, tab):
        if tab not in self._tabs:
            logging.error('SettingsWindow: Tab "%s" not found!', tab)
            return

        self.win.layout.removeWidget(self.win.currentTab)
        self.win.currentTab.hide()
        self.win.currentTab = getattr(self._tabs[tab], 'win', self._tabs[tab])
        self.win.layout.addWidget(self.win.currentTab)
        self.win.currentTab.show()

    def select_tab(self, item, prev):
        self.show_tab(item.text(0))

    def update_repo_list(self):
        tab = self._tabs['Mod sources']
        tab.sourceList.clear()

        for i, r in enumerate(center.settings['repos']):
            item = QtWidgets.QListWidgetItem(r[1], tab.sourceList)
            item.setData(QtCore.Qt.UserRole, i)

    def _edit_repo(self, repo_=None, idx=None):
        win = util.init_ui(Ui_AddRepo(), QDialog(self.win))
        win.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        win.okButton.clicked.connect(win.accept)
        win.cancelButton.clicked.connect(win.reject)

        if repo_ is not None:
            win.source.setText(repo_[0])
            win.title.setText(repo_[1])

        if win.exec_() == QtWidgets.QMessageBox.Accepted:
            source = win.source.text()
            title = win.title.text()

            if idx is None:
                found = False

                for r_source, r_title in center.settings['repos']:
                    if r_source == source:
                        found = True
                        QtWidgets.QMessageBox.critical(self.win, 'Error', 'This source is already in the list! (As "%s")' % (r_title))
                        break

                if not found:
                    center.settings['repos'].append((source, title))
            else:
                center.settings['repos'][idx] = (source, title)

            api.save_settings()
            self.update_repo_list()

        win.deleteLater()

    def add_repo(self):
        self._edit_repo()

    def edit_repo(self):
        tab = self._tabs['Mod sources']
        item = tab.sourceList.currentItem()
        if item is not None:
            idx = item.data(QtCore.Qt.UserRole)
            self._edit_repo(center.settings['repos'][idx], idx)

    def remove_repo(self):
        tab = self._tabs['Mod sources']
        item = tab.sourceList.currentItem()
        if item is not None:
            idx = item.data(QtCore.Qt.UserRole)
            answer = QtWidgets.QMessageBox.question(self.win, 'Are you sure?', 'Do you really want to remove "%s"?' % (item.text()),
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

            if answer == QtWidgets.QMessageBox.Yes:
                del center.settings['repos'][idx]

                api.save_settings()
                self.update_repo_list()

    def reorder_repos(self, parent, s_start, s_end, d_parent, d_row):
        tab = self._tabs['Mod sources']
        repos = []
        for row in range(0, tab.sourceList.count()):
            item = self.win.sourceList.item(row)
            repos.append(center.settings['repos'][item.data(QtCore.Qt.UserRole)])

        center.settings['repos'] = repos
        api.save_settings()

        # NOTE: This call is normally redundant but I want to make sure that
        # the displayed list is always the same as the actual list in settings['repos'].
        # Once this feature is stable this call can be removed.
        self.update_repo_list()

    def update_max_downloads(self, num=None):
        old_num = center.settings['max_downloads']
        center.settings['max_downloads'] = num = self._tabs['Launcher settings'].maxDownloads.value()

        if num != old_num:
            util.DL_POOL.set_capacity(num)
            api.save_settings()

    def get_ratio(self, w, h):
        w = int(w)
        h = int(h)
        ratio = (1.0 * w / h)
        ratio = '{:.1f}'.format(ratio)
        if ratio == '1.3':
            ratio_string = '4:3'
        elif ratio == '1.6':
            ratio_string = '16:10'
        elif ratio == '1.8':
            ratio_string = '16:9'
        else:
            ratio_string = 'custom'
        return ratio_string

    @staticmethod
    def has_config():
        if sys.platform.startswith('win'):
            config = QtCore.QSettings('HKEY_LOCAL_MACHINE\\Software\\Volition\\Freespace2', QtCore.QSettings.NativeFormat)
        else:
            config_file = os.path.join(api.get_fso_profile_path(), 'fs2_open.ini')
            config = QtCore.QSettings(config_file, QtCore.QSettings.IniFormat)

        if not sys.platform.startswith('win'):
            config.beginGroup('Default')

        return config.contains('VideocardFs2open')

    def get_deviceinfo(self):
        try:
            info = json.loads(util.check_output(launcher.get_cmd(['--deviceinfo'])).strip())
        except:
            logging.exception('Failed to retrieve device info!')

            QtWidgets.QMessageBox.critical(None, 'Knossos',
                'There was an error trying to retrieve your device info (screen resolution, joysticks and audio devices). ' +
                'Please try again or report this error on the HLP thread.')
            return None

        return info

    def read_config(self):
        fs2_path = center.settings['fs2_path']
        fs2_bin = center.settings['fs2_bin']

        tab = self._tabs['Game settings']
        tab.fs2PathLabel.setText(fs2_path)
        tab.build.clear()

        if fs2_path is not None:
            self._builds = bins = api.get_executables()

            idx = 0
            for name, path in bins:
                tab.build.addItem(name)

                if path == fs2_bin:
                    tab.build.setCurrentIndex(idx)

                idx += 1

            if len(bins) == 1:
                # Found only one binary, select it by default.
                tab.build.setEnabled(False)
                self.save_build()

        dev_info = self.get_deviceinfo()

        # ---Read fs2_open.ini or the registry---
        if sys.platform.startswith('win'):
            self.config = config = QtCore.QSettings('HKEY_LOCAL_MACHINE\\Software\\Volition\\Freespace2', QtCore.QSettings.NativeFormat)
        else:
            config_file = os.path.join(api.get_fso_profile_path(), 'fs2_open.ini')
            self.config = config = QtCore.QSettings(config_file, QtCore.QSettings.IniFormat)

        # Be careful with any change, the keys are all case sensitive.
        if not sys.platform.startswith('win'):
            config.beginGroup('Default')

        # video settings
        if config.contains('VideocardFs2open'):
            rawres = config.value('VideocardFs2open')
            res = rawres.split('(')[1].split(')')[0]
            res_width, res_height = res.split('x')
            depth = rawres.split(')x')[1][0:2]

            try:
                res_width = int(res_width)
                res_height = int(res_height)
            except TypeError:
                res_width = res_height = None
        else:
            res_width = None
            res_height = None
            depth = None

        texfilter = config.value('TextureFilter', None)
        af = config.value('OGL_AnisotropicFilter', None)
        aa = config.value('OGL_AntiAliasSamples', None)

        # joysticks
        joystick_id = config.value('CurrentJoystick', None)

        # network settings
        net_connection = config.value('NetworkConnection', None)
        net_speed = config.value('ConnectionSpeed', None)
        net_port = config.value('ForcePort', None)
        if not sys.platform.startswith('win'):
            config.endGroup()

        net_ip = config.value('Network/CustomIP', None)

        config.beginGroup('Sound')

        # sound settings
        playback_device = config.value('PlaybackDevice', None)
        capture_device = config.value('CaptureDevice', None)
        enable_efx = config.value('EnableEFX', None)
        sample_rate = config.value('SampleRate', None)

        config.endGroup()

        # ---Video settings---
        # Screen resolution
        vid_res = self._tabs['Video'].resolution
        vid_res.clear()

        modes = []
        if dev_info:
            for mode in dev_info['modes']:
                if mode not in modes and not (mode[0] < 800 or mode[1] < 600):
                    modes.append(mode)

        for i, (width, height) in enumerate(modes):
            vid_res.addItem('{0} x {1} ({2})'.format(width, height, self.get_ratio(width, height)))

            if width == res_width and height == res_height:
                vid_res.setCurrentIndex(i)

        # Screen depth
        vid_depth = self._tabs['Video'].colorDepth
        vid_depth.clear()
        vid_depth.addItems(['32-bit', '16-bit'])

        index = vid_depth.findText('{0}-bit'.format(depth))
        if index != -1:
            vid_depth.setCurrentIndex(index)

        # Texture filter
        vid_texfilter = self._tabs['Video'].textureFilter
        vid_texfilter.clear()
        vid_texfilter.addItems(['Bilinear', 'Trilinear'])

        try:
            index = int(texfilter)
        except TypeError:
            index = 0

        # If the SCP adds a new texture filder, we should change this part.
        if index > 1:
            index = 0
        vid_texfilter.setCurrentIndex(index)

        # Antialiasing
        vid_aa = self._tabs['Video'].antialiasing
        vid_aa.clear()
        vid_aa.addItems(['Off', '2x', '4x', '8x', '16x'])

        index = vid_aa.findText('{0}x'.format(aa))
        if index == -1:
            index = 0
        vid_aa.setCurrentIndex(index)

        # Anisotropic filtering
        vid_af = self._tabs['Video'].anisotropic
        vid_af.clear()
        vid_af.addItems(['Off', '1x', '2x', '4x', '8x', '16x'])

        index = vid_af.findText('{0}x'.format(af))
        if index == -1:
            index = 0
        vid_af.setCurrentIndex(index)

        # ---Sound settings---
        if dev_info and dev_info['audio_devs']:
            snd_devs, snd_default, snd_captures, snd_default_capture = dev_info['audio_devs']
            snd_playback = self._tabs['Audio'].playbackDevice
            snd_capture = self._tabs['Audio'].captureDevice
            snd_playback.clear()
            snd_capture.clear()

            for name in snd_devs:
                snd_playback.addItem(name)

            if playback_device is not None:
                index = snd_playback.findText(playback_device)
                if index == -1:
                    index = snd_playback.findText(snd_default)

            if index != -1:
                snd_playback.setCurrentIndex(index)

            # Fill input device combobox:
            for name in snd_captures:
                snd_capture.addItem(name)

            if capture_device is not None:
                index = snd_capture.findText(capture_device)
                if index == -1:
                    index = snd_capture.findText(snd_default_capture)

            if index != -1:
                snd_capture.setCurrentIndex(index)

            # Fill sample rate textbox :
            snd_samplerate = self._tabs['Audio'].sampleRate
            if util.is_number(sample_rate):
                sample_rate = int(sample_rate)
                if sample_rate > 0 and sample_rate < 1000000:
                    snd_samplerate.setValue(sample_rate)
                else:
                    snd_samplerate.setValue(44100)
            else:
                snd_samplerate.setValue(44100)

            # Fill EFX checkbox :
            if enable_efx == '1':
                self._tabs['Audio'].enableEFX.setChecked(True)
            else:
                self._tabs['Audio'].enableEFX.setChecked(False)

        # ---Joystick settings---
        joysticks = dev_info['joysticks'] if dev_info else []
        ctrl_joystick = self._tabs['Input'].controller

        ctrl_joystick.clear()
        ctrl_joystick.addItem('No Joystick')
        for joystick in joysticks:
            ctrl_joystick.addItem(joystick)

        if util.is_number(joystick_id):
            if joystick_id == '99999':
                ctrl_joystick.setCurrentIndex(0)
            else:
                ctrl_joystick.setCurrentIndex(int(joystick_id) + 1)
                if ctrl_joystick.currentText() == '':
                    ctrl_joystick.setCurrentIndex(0)
        else:
            ctrl_joystick.setCurrentIndex(0)

        if len(joysticks) == 0:
            ctrl_joystick.setEnabled(False)

        # ---Keyboard settings---
        kls = self._tabs['Input'].keyLayout
        if sys.platform.startswith('linux'):
            kls.clear()
            for i, layout in enumerate(('default (qwerty)', 'qwertz', 'azerty')):
                kls.addItem(layout)
                if layout == center.settings['keyboard_layout']:
                    kls.setCurrentIndex(i)

            if center.settings['keyboard_setxkbmap']:
                self._tabs['Input'].useSetxkbmap.setChecked(True)
            else:
                self._tabs['Input'].useSetxkbmap.setChecked(False)
        else:
            kls.setDisabled(True)
            self._tabs['Input'].useSetxkbmap.setDisabled(True)

        # ---Network settings---
        net_type = self._tabs['Network'].connectionType
        net_speed = self._tabs['Network'].connectionSpeed
        net_ip_f = self._tabs['Network'].forceAddress
        net_port_f = self._tabs['Network'].localPort

        net_type.clear()
        net_type.addItems(['None', 'Dialup', 'Broadband/LAN'])
        net_connections_read = {'none': 0, 'dialup': 1, 'LAN': 2}
        if net_connection in net_connections_read:
            index = net_connections_read[net_connection]
        else:
            index = 2

        net_type.setCurrentIndex(index)

        net_speed.clear()
        net_speed.addItems(['None', '28k modem', '56k modem', 'ISDN', 'DSL', 'Cable/LAN'])
        net_speeds_read = {'none': 0, 'Slow': 1, '56K': 2, 'ISDN': 3, 'Cable': 4, 'Fast': 5}
        if net_speed in net_speeds_read:
            index = net_speeds_read[net_speed]
        else:
            index = 5

        net_speed.setCurrentIndex(index)
        net_ip_f.setText(net_ip)
        net_port_f.setText(net_port)

    def write_config(self):
        config = self.config

        if sys.platform.startswith('win'):
            section = ''
        else:
            config.beginGroup('Default')
            section = 'Default/'

        # Getting ready to write key=value pairs to the ini file
        # Set video
        new_res_width, new_res_height = self._tabs['Video'].resolution.currentText().split(' (')[0].split(' x ')
        new_depth = self._tabs['Video'].colorDepth.currentText().split('-')[0]
        new_res = 'OGL -({0}x{1})x{2} bit'.format(new_res_width, new_res_height, new_depth)
        config.setValue('VideocardFs2open', new_res)

        new_texfilter = self._tabs['Video'].textureFilter.currentIndex()
        config.setValue('TextureFilter', new_texfilter)

        new_aa = self._tabs['Video'].antialiasing.currentText().split('x')[0]
        config.setValue('OGL_AntiAliasSamples', new_aa)

        new_af = self._tabs['Video'].anisotropic.currentText().split('x')[0]
        config.setValue('OGL_AnisotropicFilter', new_af)

        if not sys.platform.startswith('win'):
            config.endGroup()

        # sound
        new_playback_device = self._tabs['Audio'].playbackDevice.currentText()
        # ^ wxlauncher uses the same string as CaptureDevice, instead of what openal identifies as the playback device ? Why ?
        # ^ So I do it the way openal is supposed to work, but I'm not sure FS2 really behaves that way
        config.setValue('Sound/PlaybackDevice', new_playback_device)
        config.setValue(section + 'SoundDeviceOAL', new_playback_device)
        # ^ Useless according to SCP members, but wxlauncher does it anyway

        new_capture_device = self._tabs['Audio'].captureDevice.currentText()
        config.setValue('Sound/CaptureDevice', new_capture_device)

        if self._tabs['Audio'].enableEFX.isChecked() is True:
            new_enable_efx = 1
        else:
            new_enable_efx = 0
        config.setValue('Sound/EnableEFX', new_enable_efx)

        new_sample_rate = self._tabs['Audio'].sampleRate.value()
        config.setValue('Sound/SampleRate', new_sample_rate)

        # joystick
        if self._tabs['Input'].controller.currentText() == 'No Joystick':
            new_joystick_id = 99999
        else:
            new_joystick_id = self._tabs['Input'].controller.currentIndex() - 1
        config.setValue(section + 'CurrentJoystick', new_joystick_id)

        # keyboard
        if sys.platform.startswith('linux'):
            key_layout = self._tabs['Input'].keyLayout.currentIndex()
            if key_layout == 0:
                key_layout = 'default'
            else:
                key_layout = self._tabs['Input'].keyLayout.itemText(key_layout)

            center.settings['keyboard_layout'] = key_layout
            center.settings['keyboard_setxkbmap'] = self._tabs['Input'].useSetxkbmap.isChecked()

        # networking
        net_types = {0: 'none', 1: 'dialup', 2: 'LAN'}
        new_net_connection = net_types[self._tabs['Network'].connectionType.currentIndex()]
        config.setValue(section + 'NetworkConnection', new_net_connection)

        net_speeds = {0: 'none', 1: 'Slow', 2: '56K', 3: 'ISDN', 4: 'Cable', 5: 'Fast'}
        new_net_speed = net_speeds[self._tabs['Network'].connectionSpeed.currentIndex()]
        config.setValue(section + 'ConnectionSpeed', new_net_speed)

        new_net_ip = self._tabs['Network'].forceAddress.text()
        if new_net_ip == '...':
            new_net_ip = ''

        if new_net_ip == '':
            config.remove('Network/CustomIP')
        else:
            config.setValue('Network/CustomIP', new_net_ip)

        new_net_port = self._tabs['Network'].localPort.text()
        if new_net_port == '0':
            new_net_port = ''

        if new_net_port == '':
            config.remove(section + 'ForcePort')
        else:
            config.setValue(section + 'ForcePort', int(new_net_port))

        # Save the new configuration.
        config.sync()
        self._tabs['Default flags'].save()
        api.save_settings()

    def select_fs2_path(self):
        api.select_fs2_path()

    def save_build(self):
        fs2_bin = self._builds[self._tabs['Game settings'].build.currentIndex()][1]
        if not os.path.isfile(os.path.join(center.settings['fs2_path'], fs2_bin)):
            return

        old_bin = center.settings['fs2_bin']
        center.settings['fs2_bin'] = fs2_bin

        if not api.get_fso_flags():
            # We failed to run FSO but why?
            rc = runner.run_fs2_silent(['-help'])
            if rc == -128:
                msg = 'The FSO binary "%s" is missing!' % fs2_bin
            elif rc == -127:
                # TODO: At this point we have run ldd twice already and the next call will run it again. Is there any way to avoid this?
                _, missing = runner.fix_missing_libs(os.path.join(center.settings['fs2_path'], fs2_bin))
                msg = 'The FSO binary "%s" is missing %s!' % (fs2_bin, util.human_list(missing))
            else:
                msg = 'The FSO binary quit with code %d!' % rc

            center.settings['fs2_bin'] = old_bin
            QtWidgets.QMessageBox.critical(None, 'Knossos', msg)
            self.read_config()
        else:
            api.save_settings()
            center.signals.fs2_bin_changed.emit()

    def save_update_settings(self, p=None):
        tab = self._tabs['Launcher settings']
        center.settings['update_channel'] = tab.updateChannel.currentText()
        center.settings['update_notify'] = tab.updateNotify.checkState() == QtCore.Qt.Checked
        api.save_settings()

    def save_report_settings(self, p=None):
        tab = self._tabs['Launcher settings']
        center.settings['use_raven'] = tab.reportErrors.checkState() == QtCore.Qt.Checked

        if center.settings['use_raven']:
            api.enable_raven()
        else:
            center.raven = None

        api.save_settings()

    def show_fso_log(self):
        logpath = os.path.join(api.get_fso_profile_path(), 'data/fs2_open.log')

        if not os.path.isfile(logpath):
            QtWidgets.QMessageBox.warning(None, 'Knossos', 'Sorry, but I can\'t find the fs2_open.log file.\nDid you run the debug build?')
        else:
            LogViewer(logpath)

    def show_knossos_log(self):
        LogViewer(launcher.log_path)

    def clear_hash_cache(self):
        util.HASH_CACHE = dict()
        run_task(CheckTask())
        QtWidgets.QMessageBox.information(None, 'Knossos', 'Done!')


class GogExtractWindow(Window):

    def __init__(self, window=True):
        super(GogExtractWindow, self).__init__(window)

        self._create_win(Ui_Gogextract)

        self.win.gogPath.textChanged.connect(self.validate)
        self.win.destPath.textChanged.connect(self.validate)

        self.win.gogButton.clicked.connect(self.select_installer)
        self.win.destButton.clicked.connect(self.select_dest)
        self.win.cancelButton.clicked.connect(self.win.close)
        self.win.installButton.clicked.connect(self.do_install)

        if window:
            self.win.setModal(True)
            self.open()

    def select_installer(self):
        path = QtWidgets.QFileDialog.getOpenFileName(self.win, 'Please select the setup_freespace2_*.exe file.',
                                                 os.path.expanduser('~/Downloads'), 'Executable (*.exe)')
        if isinstance(path, tuple):
            path = path[0]

        if path is not None and path != '':
            if not os.path.isfile(path):
                QtWidgets.QMessageBox.critical(self.win, 'Not a file', 'Please select a proper file!')
                return

            self.win.gogPath.setText(os.path.abspath(path))

    def select_dest(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self.win, 'Please select the destination directory.', os.path.expanduser('~/Documents'))

        if path is not None and path != '':
            if not os.path.isdir(path):
                QtWidgets.QMessageBox.critical(self.win, 'Not a directory', 'Please select a proper directory!')
                return

            self.win.destPath.setText(os.path.abspath(path))

    def validate(self):
        if os.path.isfile(self.win.gogPath.text()) and os.path.isdir(self.win.destPath.text()):
            self.win.installButton.setEnabled(True)
        else:
            self.win.installButton.setEnabled(False)

    def do_install(self):
        # Just to be sure...
        if os.path.isfile(self.win.gogPath.text()) and os.path.isdir(self.win.destPath.text()):
            center.main_win.update_mod_buttons('progress')

            run_task(GOGExtractTask(self.win.gogPath.text(), self.win.destPath.text()))

            if self._is_window:
                self.close()


class FlagsWindow(Window):
    _flags = None
    _selected = None
    _mod = None
    _mod_arg = ''

    def __init__(self, mod=None, window=True):
        super(FlagsWindow, self).__init__(window)

        self._selected = []
        self._mod = mod

        self._create_win(Ui_Flags)
        if window:
            self.win.setModal(True)

            self.win.okButton.clicked.connect(self.win.accept)
            self.win.cancelButton.clicked.connect(self.win.reject)
            self.win.accepted.connect(self.save)
            self.win.saveButton.hide()
        else:
            self.win.saveButton.clicked.connect(self.save)
            self.win.okButton.hide()
            self.win.cancelButton.hide()

        self.win.easySetup.activated.connect(self._set_easy)
        self.win.easySetup.activated.connect(self.update_display)
        self.win.listType.activated.connect(self._update_list)
        self.win.customFlags.textEdited.connect(self.update_display)
        self.win.flagList.itemClicked.connect(self.update_display)

        self.win.defaultsButton.clicked.connect(self.set_defaults)

        if window:
            self.open()

        if mod is None:
            self.win.defaultsButton.hide()
        else:
            try:
                self._mod_arg = ','.join(mod.get_mod_flag())
            except repo.ModNotFound:
                pass

        self.read_flags()

    def read_flags(self):
        flags = api.get_fso_flags()

        if flags is None:
            self.win.setEnabled(False)
            self.win.cmdLine.setPlainText('Until you select a working FS2 build, I won\'t be able to help you.')
            return

        self.win.setEnabled(True)
        self.win.easySetup.clear()
        self.win.listType.clear()

        for key, name in flags.easy_flags.items():
            self.win.easySetup.addItem(name, key)

        self._flags = flags.flags
        for name in self._flags:
            self.win.listType.addItem(name)

        self.set_selection(api.get_cmdline(self._mod))

    def _set_easy(self):
        if self._flags is None:
            return

        combo = self.win.easySetup
        cur_mode = combo.itemData(combo.currentIndex())

        # Update self._selected.
        self.get_selection()

        for flags in self._flags.values():
            for info in flags:
                if info['on_flags'] & cur_mode == cur_mode and info['name'] not in self._selected:
                    self._selected.append(info['name'])

                if info['off_flags'] & cur_mode == cur_mode and info['name'] in self._selected:
                    self._selected.remove(info['name'])

        self._update_list(save_selection=False)

    def _update_list(self, idx=None, save_selection=True):
        if self._flags is None:
            return

        cur_type = self.win.listType.currentText()

        if save_selection:
            # Remember the currently selected options.
            self.get_selection()

        self.win.flagList.clear()
        for flag in self._flags[cur_type]:
            label = flag['desc']
            if label == '':
                label = flag['name']

            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, flag['name'])
            if flag['name'] in self._selected:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)

            self.win.flagList.addItem(item)

    def get_selection(self, split_mod_flag=False):
        count = self.win.flagList.count()

        for i in range(count):
            item = self.win.flagList.item(i)
            flag = item.data(QtCore.Qt.UserRole)
            if item.checkState() == QtCore.Qt.Checked:
                if flag not in self._selected:
                    self._selected.append(flag)
            else:
                if flag in self._selected:
                    self._selected.remove(flag)

        try:
            custom = shlex.split(self.win.customFlags.text())
        except ValueError:
            # Invalid user input...
            custom = []

        if split_mod_flag:
            idx = -1
            for i, flag in enumerate(custom):
                if flag == '-mod':
                    idx = i
                    break

            if idx > -1 and idx + 1 < len(custom):
                mod_arg = ['-mod', custom[idx + 1]]
                custom = custom[:idx] + custom[idx + 2:]
            else:
                mod_arg = []

            return self._selected + custom, mod_arg
        else:
            return self._selected + custom

    def update_display(self):
        fs2_bin = os.path.join(center.settings['fs2_path'], center.settings['fs2_bin'])
        sel, mod_flag = self.get_selection(True)
        if self._mod is not None:
            if len(mod_flag) > 0:
                mod_flag[1] = mod_flag[1].strip(',') + ',' + self._mod_arg
            else:
                mod_flag = ['-mod', self._mod_arg]

        cmdline = ' '.join([fs2_bin] + [shlex.quote(opt) for opt in sel + mod_flag])

        self.win.cmdLine.setPlainText(cmdline)

    def set_selection(self, flags):
        self._selected = flags[:]
        custom = []
        all_flags = []

        for flags in self._flags.values():
            for info in flags:
                all_flags.append(info['name'])

        for opt in self._selected[:]:
            if opt not in all_flags:
                custom.append(shlex.quote(opt))
                self._selected.remove(opt)

        self.win.customFlags.setText(' '.join(custom))
        self._update_list(save_selection=False)
        self.update_display()

    def set_defaults(self):
        cmdlines = center.settings['cmdlines']

        if '#default' in cmdlines:
            self.set_selection(cmdlines['#default'])
        else:
            self.set_selection([])

        self.save()

    def save(self):
        sel = self.get_selection()
        clines = center.settings['cmdlines']

        if self._mod is None:
            clines['#default'] = self.get_selection()
        else:
            mid = self._mod.mid
            if sel == clines['#default']:
                logging.info('Not saving default flags!')
                if mid in clines:
                    del clines[mid]
            else:
                clines[mid] = self.get_selection()

        api.save_settings()


class ModInstallWindow(Window):
    _mod = None
    _pkg_checks = None
    _dep_tpl = None

    def __init__(self, mod, sel_pkgs=[]):
        super(ModInstallWindow, self).__init__()

        self._mod = mod
        self._create_win(Ui_Install)
        self.win.splitter.setStretchFactor(0, 2)
        self.win.splitter.setStretchFactor(1, 1)

        self.label_tpl(self.win.titleLabel, MOD=mod.title)
        self.win.notesField.setPlainText(mod.notes)

        self._pkg_checks = []
        self.show_packages()
        self.update_deps()

        self.win.treeWidget.itemChanged.connect(self.update_selection)

        self.win.accepted.connect(self.install)
        self.win.rejected.connect(self.close)

        self.open()

    def show_packages(self):
        pkgs = self._mod.packages
        try:
            all_pkgs = center.mods.process_pkg_selection(pkgs)
        except repo.ModNotFound as exc:
            logging.exception('Well, I won\'t be installing that...')
            msg = 'I\'m sorry but you won\'t be able to install "%s" because "%s" is missing!' % (self._mod.title, exc.mid)
            QtWidgets.QMessageBox.critical(None, 'Knossos', msg)

            self.close()
            return

        needed_pkgs = self._mod.resolve_deps()
        mods = set()

        for pkg in all_pkgs:
            mods.add(pkg.get_mod())

        # Make sure our current mod comes first.
        if self._mod in mods:
            mods.remove(self._mod)

        mods = [self._mod] + list(mods)
        for mod in mods:
            item = QtWidgets.QTreeWidgetItem(self.win.treeWidget, [mod.title, ''])
            item.setExpanded(True)
            item.setData(0, QtCore.Qt.UserRole, mod)
            c = 0

            for pkg in mod.packages:
                fsize = 0
                for f_item in pkg.files.values():
                    fsize += f_item.get('filesize', 0)

                if fsize > 0:
                    fsize = util.format_bytes(fsize)
                else:
                    fsize = '?'

                sub = QtWidgets.QTreeWidgetItem(item, [pkg.name, fsize])
                is_installed = center.installed.is_installed(pkg)

                if is_installed:
                    sub.setText(1, 'Installed')

                if pkg.status == 'required' or pkg in needed_pkgs or is_installed:
                    sub.setCheckState(0, QtCore.Qt.Checked)
                    sub.setDisabled(True)

                    c += 1
                elif pkg.status == 'recommended':
                    sub.setCheckState(0, QtCore.Qt.Checked)
                    c += 1
                if pkg.status == 'optional':
                    sub.setCheckState(0, QtCore.Qt.Unchecked)

                sub.setData(0, QtCore.Qt.UserRole, pkg)
                sub.setData(0, QtCore.Qt.UserRole + 1, is_installed)
                self._pkg_checks.append(sub)

            if c == len(mod.packages):
                item.setCheckState(0, QtCore.Qt.Checked)
            elif c > 0:
                item.setCheckState(0, QtCore.Qt.PartiallyChecked)
            else:
                item.setCheckState(0, QtCore.Qt.Unchecked)

        self.win.treeWidget.header().resizeSections(QtWidgets.QHeaderView.ResizeToContents)

    def update_selection(self, item, col):
        obj = item.data(0, QtCore.Qt.UserRole)
        if isinstance(obj, repo.Mod):
            cs = item.checkState(0)

            for i in range(item.childCount()):
                child = item.child(i)
                if not child.isDisabled():
                    child.setCheckState(0, cs)

        self.update_deps()

    def get_selected_pkgs(self):
        pkgs = []
        for item in self._pkg_checks:
            if item.checkState(0) == QtCore.Qt.Checked:
                pkgs.append(item.data(0, QtCore.Qt.UserRole))

        pkgs = center.mods.process_pkg_selection(pkgs)
        return pkgs

    def update_deps(self):
        pkg_sel = self.get_selected_pkgs()
        dl_size = 0
        for item in self._pkg_checks:
            pkg = item.data(0, QtCore.Qt.UserRole)

            if not item.data(0, QtCore.Qt.UserRole + 1):
                if item.checkState(0) == QtCore.Qt.Checked or pkg in pkg_sel:
                    for f_item in pkg.files.values():
                        dl_size += f_item.get('filesize', 0)

            if item.isDisabled():
                continue

            if pkg in pkg_sel:
                item.setCheckState(0, QtCore.Qt.Checked)

        self.label_tpl(self.win.dlSizeLabel, DL_SIZE=util.format_bytes(dl_size))

    def install(self):
        center.main_win.update_mod_buttons('progress')

        run_task(InstallTask(self.get_selected_pkgs(), self._mod))
        self.close()


class ModSettingsWindow(Window):
    _mod = None
    _pkg_checks = None
    _mod_versions = None
    _flags = None

    def __init__(self, mod, window=True):
        super(ModSettingsWindow, self).__init__(window)

        self._mod = mod
        self._mod_versions = []
        self._create_win(Ui_Mod_Settings, QDialog)
        self.load_styles(':/ui/themes/default/mod_settings.css')

        self.win.modTitle.setText(self._mod.title)
        self.win.modLogo.setPixmap(QtGui.QPixmap(mod.logo_path))
        self.win.modDesc.setPlainText(mod.description)

        lay = QtWidgets.QVBoxLayout(self.win.flagsTab)
        self._flags = FlagsWindow(mod, False)
        lay.addWidget(self._flags.win)

        self._pkg_checks = []
        if isinstance(mod, repo.IniMod):
            self.win.tabWidget.setTabEnabled(2, False)  # Packages
            self.win.tabWidget.setTabEnabled(3, False)  # Versions
            self.win.tabWidget.setTabEnabled(4, False)  # Troubleshooting
        else:
            try:
                rmod = center.mods.query(mod)
            except repo.ModNotFound:
                rmod = mod

            for pkg in rmod.packages:
                p_check = QtWidgets.QCheckBox(pkg.name)
                installed = center.installed.is_installed(pkg)

                if pkg.status == 'required' or installed:
                    p_check.setCheckState(QtCore.Qt.Checked)

                    if pkg.status == 'required':
                        p_check.setDisabled(True)

                        if not installed:
                            p_check.setProperty('error', True)
                            p_check.setText(pkg.name + ' (missing)')
                else:
                    p_check.setCheckState(QtCore.Qt.Unchecked)

                p_check.stateChanged.connect(self.update_dlsize)
                self.win.pkgsLayout.addWidget(p_check)
                self._pkg_checks.append([p_check, installed, pkg])

            settings = center.settings['mod_settings'].get(self._mod.mid)
            if settings:
                if settings.get('parse_mod_ini', False):
                    self.win.parseModIni.setCheckState(QtCore.Qt.Checked)
                else:
                    self.win.parseModIni.setCheckState(QtCore.Qt.Unchecked)

            self.win.applyPkgChanges.clicked.connect(self.apply_pkg_selection)

            self.win.parseModIni.stateChanged.connect(self.apply_mod_ini_setting)
            self.win.checkFiles.clicked.connect(self.check_files)
            self.win.delLoose.clicked.connect(self.delete_loose_files)
            self.win.replaceFiles.clicked.connect(self.repair_files)

            self.update_dlsize()
            self.show_versions()

        center.signals.repo_updated.connect(self.update_repo_related)

        self.show_flags_tab()
        self.open()

    def _del(self):
        center.signals.repo_updated.disconnect(self.update_repo_related)

        super(ModSettingsWindow, self)._del()

    def update_repo_related(self):
        try:
            self._mod = center.installed.query(self._mod)
        except repo.ModNotFound:
            self.close()

            # Try to open a new window showing the latest version.
            try:
                m2 = center.installed.query(self._mod.mid)
            except repo.ModNotFound:
                pass
            else:
                ModSettingsWindow(m2)

            return

        self.show_versions()

        for i, item in enumerate(self._pkg_checks):
            checked = item[0].checkState() == QtCore.Qt.Checked
            was_inst = item[1]
            is_inst = center.installed.is_installed(item[2])

            if was_inst != is_inst:
                if checked == was_inst:
                    if is_inst:
                        item[0].setCheckState(QtCore.Qt.Checked)
                    else:
                        item[0].setCheckState(QtCore.Qt.Unchecked)

                if is_inst and item[0].property('error'):
                    item[0].setProperty('error', False)
                    item[0].setText(item[2].name)
                elif not is_inst and item[2].status == 'required' and not item[0].property('error'):
                    item[0].setProperty('error', True)
                    item[0].setText(item[2].name + ' (missing)')

                item[1] = is_inst

        self.update_dlsize()

    def show_flags_tab(self):
        self.win.tabWidget.setCurrentIndex(0)

    def show_pkg_tab(self):
        self.win.tabWidget.setCurrentIndex(1)

    def get_selected_pkgs(self):
        install = []
        remove = []

        for check, is_installed, pkg in self._pkg_checks:
            selected = check.checkState() == QtCore.Qt.Checked
            if selected != is_installed:
                if selected:
                    install.append(pkg)
                else:
                    remove.append(pkg)

        if len(install) > 0:
            try:
                install = center.mods.process_pkg_selection(install)
            except repo.ModNotFound as exc:
                if center.mods.has(self._mod):
                    QtWidgets.QMessageBox.critical(None, 'Knossos', "I'm sorry but I can't install the selected packages because some the dependency \"%s\" is missing!" % exc.mid)
                else:
                    QtWidgets.QMessageBox.critical(None, 'Knossos', "I'm sorry but I can't install new packages for this mod since it's not available anymore!")

                install = []

        remove = list(set(remove) - set(install))

        return install, remove

    def update_dlsize(self):
        install, remove = self.get_selected_pkgs()
        try:
            all_pkgs = center.mods.process_pkg_selection(install)
        except repo.ModNotFound:
            all_pkgs = []

        dl_size = 0

        for pkg in all_pkgs:
            if not center.installed.is_installed(pkg):
                for item in pkg.files.values():
                    dl_size += item.get('filesize', 0)

        self.label_tpl(self.win.dlSizeLabel, DL_SIZE=util.format_bytes(dl_size))

    def apply_pkg_selection(self):
        install, remove = self.get_selected_pkgs()

        if len(remove) == 0 and len(install) == 0:
            # Nothing to do...
            return

        msg = ''
        if len(remove) > 0:
            msg += "I'm going to remove " + util.human_list([p.name for p in remove]) + ".\n"

        if len(install) > 0:
            msg += "I'm going to install " + util.human_list([p.name for p in install if not center.installed.is_installed(p)]) + ".\n"

        box = QtWidgets.QMessageBox()
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setText(msg)
        box.setInformativeText('Continue?')
        box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        box.setDefaultButton(QtWidgets.QMessageBox.Yes)

        if box.exec_() == QtWidgets.QMessageBox.Yes:
            run_task(UninstallTask(remove))
            run_task(InstallTask(install))

    def show_versions(self):
        mods = set()
        try:
            for dep in self._mod.resolve_deps():
                mods.add(dep.get_mod())
        except repo.ModNotFound as exc:
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'This mod is missing the dependency "%s"!' % exc.mid)
            return

        mods.add(self._mod)

        layout = self.win.versionsTab.layout()
        if layout:
            # Clear the current layout
            item = layout.takeAt(0)
            while item:
                w = item.widget()
                if w:
                    w.deleteLater()

                item = layout.takeAt(0)
        else:
            layout = QtWidgets.QGridLayout()
            self.win.versionsTab.setLayout(layout)

        mods = sorted(mods, key=lambda m: m.title)
        for i, mod in enumerate(mods):
            versions = list(center.installed.query_all(mod.mid))
            label = QtWidgets.QLabel(mod.title + ': ')
            label.setWordWrap(True)

            sel = QtWidgets.QComboBox()
            sel.addItem('Latest (%s)' % versions[0].version, None)

            pin = center.installed.get_pin(mod)
            for n, mv in enumerate(versions):
                sel.addItem(str(mv.version), mv.version)

                if pin == mv.version:
                    sel.setCurrentIndex(n + 1)

            editBut = QtWidgets.QPushButton('Edit')

            layout.addWidget(label, i, 0)
            layout.addWidget(sel, i, 1)
            layout.addWidget(editBut, i, 2)

            if mod == self._mod:
                cb_sel = functools.partial(self.update_versions, sel, mod)
                cb_edit = functools.partial(self.open_ver_edit, mod)

                sel.currentIndexChanged.connect(cb_sel)
                editBut.clicked.connect(cb_edit)
            else:
                # TODO: Finish code for pinning dependencies.
                sel.setEnabled(False)
                editBut.setEnabled(False)

        layout.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

    def update_versions(self, sel, mod, idx):
        version = sel.itemData(idx)

        if mod == self._mod:
            if version is None:
                center.installed.unpin(self._mod)
            else:
                if isinstance(version, str):
                    version = semantic_version.Version(version)

                center.installed.pin(self._mod, version)

            api.save_settings()
        else:
            raise NotImplemented

    def open_ver_edit(self, mod):
        ModVersionsWindow(mod)

    def apply_mod_ini_setting(self, state):
        settings = center.settings['mod_settings']
        if self._mod.mid not in settings:
            settings[self._mod.mid] = {}

        settings = settings[self._mod.mid]
        settings['parse_mod_ini'] = state == QtCore.Qt.Checked
        api.save_settings()

    def check_files(self):
        self.win.setCursor(QtCore.Qt.BusyCursor)

        task = CheckFilesTask(self._mod)
        task.done.connect(functools.partial(self.__check_files, task))
        run_task(task)

    def __check_files(self, task):
        report = ''

        for pkg, s, c, info in task.get_results():
            if pkg is None:
                if len(info['loose']) > 0:
                    report += '<h2>Loose files (%d)</h2>' % (len(info['loose']))
                    report += '<ul><li>' + '</li><li>'.join(sorted(info['loose'])) + '</li></ul>'
            else:
                report += '<h2>%s (%d/%d files OK)</h2>' % (pkg.name, s, c)
                ok_count = len(info['ok'])
                corr_count = len(info['corrupt'])
                miss_count = len(info['missing'])

                report += '<ul>'

                if ok_count > 0:
                    if corr_count > 0 or miss_count > 0:
                        report += '<ul><li>OK<ul>'
                        report += '<li>' + '</li><li>'.join(sorted(info['ok'])) + '</li>'
                        report += '</ul></li>'
                    else:
                        report += '<li>' + '</li><li>'.join(sorted(info['ok'])) + '</li>'

                if corr_count > 0:
                    report += '<li>Corrupted<ul>'
                    report += '<li>' + '</li><li>'.join(sorted(info['corrupt'])) + '</li>'
                    report += '</ul></li>'

                if miss_count > 0:
                    report += '<li>Missing<ul>'
                    report += '<li>' + '</li><li>'.join(sorted(info['missing'])) + '</li>'
                    report += '</ul></li>'

                report += '</ul>'

        self.win.logDisplay.setHtml(report)
        self.win.unsetCursor()

    def delete_loose_files(self):
        self.win.setCursor(QtCore.Qt.BusyCursor)

        task = CheckFilesTask(self._mod)
        task.done.connect(functools.partial(self.__delete_loose_files, task))
        run_task(task)

    # TODO: Should this be moved into a task?
    def __delete_loose_files(self, task):
        modpath = os.path.join(center.settings['fs2_path'], self._mod.folder)

        for pkg, s, c, info in task.get_results():
            if pkg is None:
                for name in info['loose']:
                    item = os.path.join(modpath, name)
                    logging.info('Deleteing "%s"...', item)
                    os.unlink(item)

        self.win.unsetCursor()
        QtWidgets.QMessageBox.information(None, 'Knossos', 'Done!')

    def repair_files(self):
        try:
            run_task(InstallTask(self._mod.packages))
        except repo.ModNotFound as exc:
            QtWidgets.QMessageBox.critical(None, 'Knossos', "I can't repair this mod: %s" % str(exc))


class ModVersionsWindow(Window):
    _mod = None
    _versions = None

    def __init__(self, mod, window=True):
        super(ModVersionsWindow, self).__init__(window)

        self._mod = mod
        self._versions = []
        self._create_win(Ui_Mod_Versions, QDialog)
        self.win.setModal(True)

        self.label_tpl(self.win.label, MOD=mod.title)

        mods = list(center.mods.query_all(mod.mid))
        installed = list(center.installed.query_all(mod.mid))

        inst_versions = [m.version for m in installed]
        rem_versions = [m.version for m in mods]
        local_versions = set(inst_versions) - set(rem_versions)

        # Add all local-only versions
        for m in installed:
            if m.version in local_versions:
                mods.append(m)

        for m in mods:
            if len(m.packages) == 0:
                logging.warning('Version "%s" for mod "%s" (%s) is empty! (It has no packages!!)', m.version, m.title, m.mid)
                continue

            label = str(m.version)
            if m.version in local_versions:
                label += ' (l)'

            item = QtWidgets.QListWidgetItem(label, self.win.versionList)
            item.setData(QtCore.Qt.UserRole + 1, m)

            if m.version in local_versions:
                item.setToolTip('This version is installed locally but not available anymore!')

            if m.version in inst_versions:
                item.setCheckState(QtCore.Qt.Checked)
                item.setData(QtCore.Qt.UserRole, True)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
                item.setData(QtCore.Qt.UserRole, False)

            self._versions.append(item)

        self.win.applyButton.clicked.connect(self.apply_changes)
        self.win.cancelButton.clicked.connect(self.close)
        self.open()

    def apply_changes(self):
        install = set()
        uninstall = set()

        for item in self._versions:
            was = item.data(QtCore.Qt.UserRole)
            mod = item.data(QtCore.Qt.UserRole + 1)
            checked = item.checkState() == QtCore.Qt.Checked

            if was and not checked:
                uninstall |= set(center.installed.query(mod).packages)
            elif not was and checked:
                install |= set(mod.resolve_deps())

        install = center.mods.process_pkg_selection(install)

        if len(install) > 0:
            run_task(InstallTask(install, self._mod))

        if len(uninstall) > 0:
            run_task(UninstallTask(uninstall))

        self.close()


class ModInfoWindow(Window):
    _mod = None

    def __init__(self, mod, window=True):
        super(ModInfoWindow, self).__init__(window)

        self._mod = mod
        self._create_win(Ui_Mod_Settings, QDialog)

        self.win.modTitle.setText(mod.title)
        self.win.modLogo.setPixmap(QtGui.QPixmap(mod.logo))
        self.win.modDesc.setPlainText(mod.description)

        self.win.flagsTab.deleteLater()
        self.win.pkgTab.deleteLater()
        self.win.versionsTab.deleteLater()
        self.win.troubleTab.deleteLater()
        self.win.tabWidget.setCurrentIndex(0)

        self.open()


class LogViewer(Window):

    def __init__(self, path, window=True):
        super(LogViewer, self).__init__(window)

        self._create_win(Ui_Log_Viewer)
        self.win.pathLabel.setText(path)

        if not os.path.isfile(path):
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'Log file %s can\'t be shown because it\'s missing!' % path)
            return

        with open(path, 'r') as stream:
            self.win.content.setPlainText(stream.read())

        self.open()
