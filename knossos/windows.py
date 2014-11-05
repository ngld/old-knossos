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
import sys
import logging
import glob
import shlex
import functools

from . import uhf
uhf(__name__)

from . import center, util, clibs, progress, integration, api, web
from .qt import QtCore, QtGui
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
from .ui.flags import Ui_Dialog as Ui_Flags
from .ui.install import Ui_Dialog as Ui_Install
from .tasks import run_task, GOGExtractTask, InstallTask

# Keep references to all open windows to prevent the GC from deleting them.
_open_wins = []


class QMainWindow(QtGui.QMainWindow):
    closed = QtCore.Signal()
    
    def closeEvent(self, e):
        self.closed.emit()
        e.accept()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.ActivationChange:
            integration.current.annoy_user(False)
    
        return super(QMainWindow, self).changeEvent(event)


class Window(object):
    win = None
    closed = True
    _is_window = True

    def __init__(self, window=True):
        self._is_window = window

    def _create_win(self, ui_class, qt_widget=util.QDialog):
        if not self._is_window:
            qt_widget = QtGui.QWidget

        return util.init_ui(ui_class(), qt_widget())
    
    def open(self):
        global _open_wins
        
        self.closed = False
        _open_wins.append(self)

        if hasattr(self.win, 'closed'):
            self.win.closed.connect(self._del)

        if hasattr(self.win, 'finished'):
            self.win.finished.connect(self._del)

        self.win.show()
    
    def close(self):
        self.win.close()
    
    def _del(self):
        # Make sure all events are processed.
        QtCore.QTimer.singleShot(3, self._del2)
    
    def _del2(self):
        global _open_wins

        self.closed = True
        if self in _open_wins:
            _open_wins.remove(self)

    def label_tpl(self, label, **vars):
        text = label.text()
        for name, value in vars.items():
            text = text.replace('{' + name + '}', value)

        label.setText(text)


class HellWindow(Window):
    _mod_tasks = None
    browser_ctrl = None
    progress_win = None

    def __init__(self, window=True):
        super(HellWindow, self).__init__(window)
        self._mod_tasks = {}

        self.win = self._create_win(Ui_Hell, QMainWindow)
        self.browser_ctrl = web.BrowserCtrl(self.win.webView)
        self.progress_win = progress.ProgressDisplay()
        self.progress_win.set_statusarea(self.win.progressInfo, self.win.progressLabel, self.win.progressBar)

        self.win.modlistButton.clicked.connect(self.show_mod_list)
        self.win.backButton.clicked.connect(self.win.webView.back)
        self.win.searchEdit.textEdited.connect(self.search_mods)
        self.win.filterSelect.currentIndexChanged.connect(self.search_mods)
        self.win.updateButton.clicked.connect(api.fetch_list)
        self.win.settingsButton.clicked.connect(self.show_settings)

        self.win.webView.loadStarted.connect(self.show_indicator)
        self.win.webView.loadFinished.connect(self.check_loaded)

        center.signals.repo_updated.connect(self.search_mods)
        center.signals.task_launched.connect(self.watch_mod_task)

        self.win.pageControls.hide()
        self.open()

        if center.settings['fs2_path'] is None:
            self.win.webView.load('qrc:///html/welcome.html')
            self.win.pageControls.setEnabled(False)

    def check_fso(self):
        if center.settings['fs2_path'] is not None:
            self.show_mod_list()
            self.update_repo_list()
            self.win.pageControls.setEnabled(True)
        else:
            self.win.webView.load('qrc:///html/welcome.html')
            self.win.pageControls.setEnabled(False)

    def update_repo_list(self):
        api.fetch_list()

    def show_mod_list(self):
        self.win.webView.load('qrc:///html/modlist.html')

    def search_mods(self):
        mode = self.win.filterSelect.currentIndex()
        mode_key = None
        mods = None

        if mode == 0:
            mods = center.installed.mods
            mode_key = 'installed'
        elif mode == 1:
            mods = {}
            mode_key = 'available'
            for mid, mvs in center.settings['mods'].mods.items():
                if mid not in center.installed.mods:
                    mods[mid] = mvs
        elif mode == 2:
            mods = {}
            mode_key = 'updates'
            for mid in center.installed.get_updates():
                mods[mid] = center.installed.mods[mid]
        elif mode == 3:
            mods = {}
            mode_key = 'downloading'
            for mid, task in self._mod_tasks.items():
                mods[mid] = [task.mod]
        
        # Now filter the mods.
        query = self.win.searchEdit.text()
        result = {}
        for mid, mvs in mods.items():
            if query in mvs[0].title:
                result[mid] = [mod.get() for mod in mvs]

        self.browser_ctrl.get_bridge().updateModlist.emit(result, mode_key)

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

            self.search_mods()
        else:
            self.win.listControls.hide()
            self.win.pageControls.show()

    def watch_mod_task(self, task):
        mod = getattr(task, 'mod', None)
        if mod is not None:
            self._mod_tasks[mod.mid] = task
            task.done.connect(functools.partial(self._forget_task, mod.mid))
            task.progress.connect(functools.partial(self._track_mod_progress, mod.mid))

    def _track_mod_progress(self, mid, pi):
        self.browser_ctrl.get_bridge().modProgress.emit(mid, pi[0], pi[1])

    def _forget_task(self, mid):
        if mid in self._mod_tasks:
            del self._mod_tasks[mid]

    def abort_mod_dl(self, mid):
        if mid in self._mod_tasks:
            self._mod_tasks[mid].abort()


class SettingsWindow(Window):
    _tabs = None

    def __init__(self):
        self._tabs = {}
        self.win = util.init_ui(Ui_Settings(), util.QDialog(center.app.activeWindow()))
        self.win.treeWidget.expandAll()
        self.win.treeWidget.clicked.connect(self.select_tab)
        self.win.saveButton.clicked.connect(self.write_config)

        self._tabs['About Knossos'] = tab = util.init_ui(Ui_Settings_About(), QtGui.QWidget())

        self._tabs['Launcher settings'] = tab = util.init_ui(Ui_Settings_Knossos(), QtGui.QWidget())
        tab.versionLabel.setText(center.VERSION)
        tab.maxDownloads.setValue(center.settings['max_downloads'])

        if center.settings['update_channel'] == 'stable':
            tab.updateChannel.setCurrentIndex(0)
        else:
            tab.updateChannel.setCurrentIndex(1)

        if center.settings['update_notify']:
            tab.updateNotify.setCheckState(QtCore.Qt.Checked)
        else:
            tab.updateNotify.setCheckState(QtCore.Qt.Unchecked)

        tab.maxDownloads.valueChanged.connect(self.update_max_downloads)
        tab.updateChannel.currentIndexChanged.connect(self.save_update_settings)
        tab.updateNotify.stateChanged.connect(self.save_update_settings)

        self._tabs['Retail install'] = tab = GogExtractWindow(False)
        tab.win.cancelButton.hide()

        self._tabs['Mod sources'] = tab = util.init_ui(Ui_Settings_Sources(), QtGui.QWidget())
        tab.addSource.clicked.connect(self.add_repo)
        tab.editSource.clicked.connect(self.edit_repo)
        tab.removeSource.clicked.connect(self.remove_repo)
        tab.sourceList.itemDoubleClicked.connect(self.edit_repo)

        self._tabs['Mod versions'] = tab = util.init_ui(Ui_Settings_Versions(), QtGui.QWidget())
        # TODO: Do we really need to implement this?
        
        self._tabs['Game settings'] = tab = util.init_ui(Ui_Settings_Fso(), QtGui.QWidget())
        tab.browseButton.clicked.connect(api.select_fs2_path)
        tab.build.activated.connect(self.save_build)

        self._tabs['Video'] = tab = util.init_ui(Ui_Settings_Video(), QtGui.QWidget())
        self._tabs['Audio'] = tab = util.init_ui(Ui_Settings_Audio(), QtGui.QWidget())
        self._tabs['Input'] = tab = util.init_ui(Ui_Settings_Input(), QtGui.QWidget())
        self._tabs['Network'] = tab = util.init_ui(Ui_Settings_Network(), QtGui.QWidget())

        self.update_repo_list()
        self.read_config()

        self.show_tab('About Knossos')
        self.open()

    def show_tab(self, tab):
        if tab not in self._tabs:
            logging.error('SettingsWindow: Tab "%s" not found!', tab)
            return

        self.win.layout.removeWidget(self.win.currentTab)
        self.win.currentTab.hide()
        self.win.currentTab = getattr(self._tabs[tab], 'win', self._tabs[tab])
        self.win.layout.addWidget(self.win.currentTab)
        self.win.currentTab.show()

    def select_tab(self, item):
        self.show_tab(item.data())

    def update_repo_list(self):
        tab = self._tabs['Mod sources']
        tab.sourceList.clear()
        
        for i, r in enumerate(center.settings['repos']):
            item = QtGui.QListWidgetItem(r[1], tab.sourceList)
            item.setData(QtCore.Qt.UserRole, i)

    def _edit_repo(self, repo_=None, idx=None):
        win = util.init_ui(Ui_AddRepo(), util.QDialog(self.win))
        
        win.okButton.clicked.connect(win.accept)
        win.cancelButton.clicked.connect(win.reject)
        
        if repo_ is not None:
            win.source.setText(repo_[0])
            win.title.setText(repo_[1])
        
        if win.exec_() == QtGui.QMessageBox.Accepted:
            source = win.source.text()
            title = win.title.text()
            
            if idx is None:
                found = False
                
                for r_source, r_title in center.settings['repos']:
                    if r_source == source:
                        found = True
                        QtGui.QMessageBox.critical(self.win, 'Error', 'This source is already in the list! (As "%s")' % (r_title))
                        break
                
                if not found:
                    center.settings['repos'].append((source, title))
            else:
                center.settings['repos'][idx] = (source, title)
            
            api.save_settings()
            self.update_repo_list()

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
            answer = QtGui.QMessageBox.question(self.win, 'Are you sure?', 'Do you really want to remove "%s"?' % (item.text()),
                                                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            
            if answer == QtGui.QMessageBox.Yes:
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
    
    def read_config(self):
        fs2_path = center.settings['fs2_path']
        fs2_bin = center.settings['fs2_bin']

        build = self._tabs['Game settings'].build
        build.clear()

        if fs2_path is not None and os.path.isdir(fs2_path):
            fs2_path = os.path.abspath(fs2_path)
            bins = glob.glob(os.path.join(fs2_path, 'fs2_open_*'))
            
            idx = 0
            for path in bins:
                path = os.path.basename(path)

                if not path.endswith(('.map', '.pdb')):
                    build.addItem(path)
                    
                    if path == fs2_bin:
                        build.setCurrentIndex(idx)

                    idx += 1
            
            if len(bins) == 1:
                # Found only one binary, select it by default.
                build.setEnabled(False)
                self.save_build()

        # ---Read fs2_open.ini or the registry---
        if sys.platform.startswith('win'):
            self.config = config = QtCore.QSettings('HKEY_LOCAL_MACHINE\\Software\\Volition\\Freespace2', QtCore.QSettings.NativeFormat)
        else:
            config_file = os.path.expanduser('~/.fs2_open/fs2_open.ini')
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

        raw_modes = clibs.get_modes()
        modes = []
        for mode in raw_modes:
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
        if clibs.can_detect_audio():
            snd_devs, snd_default, snd_captures, snd_default_capture = clibs.list_audio_devs()
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
        joysticks = clibs.list_joysticks()
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
        
        #---Keyboard settings---
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

        #---Network settings---
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
        api.save_settings()

    def save_build(self):
        fs2_bin = str(self.win.build.currentText())
        if not os.path.isfile(os.path.join(center.settings['fs2_path'], fs2_bin)):
            return

        center.settings['fs2_bin'] = fs2_bin
        api.get_fso_flags()
        api.save_settings()

    def save_update_settings(self, p=None):
        tab = self._tabs['Launcher settings']
        center.settings['update_channel'] = tab.updateChannel.currentText()
        center.settings['update_notify'] = tab.updateNotify.checkState() == QtCore.Qt.Checked
        api.save_settings()


class GogExtractWindow(Window):

    def __init__(self, window=True):
        super(GogExtractWindow, self).__init__(window)

        self.win = self._create_win(Ui_Gogextract)
        self.win.setParent(center.app.activeWindow())

        self.win.gogPath.textChanged.connect(self.validate)
        self.win.destPath.textChanged.connect(self.validate)

        self.win.gogButton.clicked.connect(self.select_installer)
        self.win.destButton.clicked.connect(self.select_dest)
        self.win.cancelButton.clicked.connect(self.win.close)
        self.win.installButton.clicked.connect(self.do_install)

        if window:
            self.open()

    def select_installer(self):
        path = QtGui.QFileDialog.getOpenFileName(self.win, 'Please select the setup_freespace2_*.exe file.',
                                                 os.path.expanduser('~/Downloads'), 'Executable (*.exe)')
        if isinstance(path, tuple):
            path = path[0]
        
        if path is not None and path != '':
            if not os.path.isfile(path):
                QtGui.QMessageBox.critical(self.win, 'Not a file', 'Please select a proper file!')
                return

            self.win.gogPath.setText(os.path.abspath(path))

    def select_dest(self):
        path = QtGui.QFileDialog.getExistingDirectory(self.win, 'Please select the destination directory.', os.path.expanduser('~/Documents'))

        if path is not None and path != '':
            if not os.path.isdir(path):
                QtGui.QMessageBox.critical(self.win, 'Not a directory', 'Please select a proper directory!')
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
            run_task(GOGExtractTask(self.win.gogPath.text(), self.win.destPath.text()))

            if self._is_window:
                self.close()


class FlagsWindow(Window):
    _flags = None
    _selected = None
    _mod = None
    
    def __init__(self, parent=None, mod=None, window=True):
        super(FlagsWindow, self).__init__(window)
        
        self._selected = []
        self._mod = mod
        
        self.win = self._create_win(Ui_Flags)
        self.win.setParent(center.app.activeWindow())
        self.win.setModal(True)
        
        self.win.easySetup.activated.connect(self._set_easy)
        self.win.easySetup.activated.connect(self.update_display)
        self.win.listType.activated.connect(self._update_list)
        self.win.customFlags.textEdited.connect(self.update_display)
        self.win.flagList.itemClicked.connect(self.update_display)
        self.win.okButton.clicked.connect(self.win.accept)
        self.win.defaultsButton.clicked.connect(self.set_defaults)
        self.win.cancelButton.clicked.connect(self.win.reject)
        
        self.win.accepted.connect(self.save)
        
        self.read_flags()
        self.open()
        
        if mod is None:
            self.win.defaultsButton.hide()

        if self._flags is not None:
            self.set_selection(api.get_cmdline(mod))
    
    def read_flags(self):
        flags = api.get_fso_flags()

        if flags is None:
            self.win.easySetup.setDisabled(True)
            self.win.listType.setDisabled(True)
            self.win.flagList.setDisabled(True)
            self.win.defaultsButton.setDisabled(True)
            return
        
        for key, name in flags.easy_flags.items():
            self.win.easySetup.addItem(name, key)
        
        self._flags = flags.flags
        for name in self._flags:
            self.win.listType.addItem(name)
        
        self._update_list(save_selection=False)
    
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
            
            item = QtGui.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, flag['name'])
            if flag['name'] in self._selected:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
            
            self.win.flagList.addItem(item)
    
    def get_selection(self):
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
        
        return self._selected + custom
    
    def update_display(self):
        fs2_bin = os.path.join(center.settings['fs2_path'], center.settings['fs2_bin'])
        cmdline = ' '.join([fs2_bin] + [shlex.quote(opt) for opt in self.get_selection()])
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
        if self._mod is None:
            center.settings['cmdlines']['#default'] = self.get_selection()
        else:
            center.settings['cmdlines'][self._mod.mid] = self.get_selection()
        
        api.save_settings()


class ModInstallWindow(Window):
    _mod = None
    _pkg_checks = None
    _dep_tpl = None

    def __init__(self, mod, sel_pkgs=[]):
        super(ModInstallWindow, self).__init__()

        self._mod = mod
        self.win = util.init_ui(Ui_Install(), util.QDialog(center.app.activeWindow()))
        dl_size = 0

        self.label_tpl(self.win.titleLabel, MOD=mod.title)
        self.label_tpl(self.win.dlSizeLabel, DL_SIZE=util.format_bytes(dl_size))

        self._pkg_checks = []
        for pkg in mod.packages:
            p_check = QtGui.QCheckBox(pkg.name)
            if pkg.status != 'optional' or pkg.name in sel_pkgs:
                p_check.setCheckState(QtCore.Qt.Checked)

            if pkg.status == 'required':
                p_check.setDisabled(True)

            p_check.stateChanged.connect(self.update_deps)
            self.win.pkgsLayout.addWidget(p_check)
            self._pkg_checks.append(p_check)

        self.update_deps()
        self.win.installButton.clicked.connect(self.install)
        self.win.cancelButton.clicked.connect(self.close)

        self.open()

    def get_selected_pkgs(self):
        pkgs = []
        for i, check in enumerate(self._pkg_checks):
            if check.checkState() == QtCore.Qt.Checked:
                pkgs.append(self._mod.packages[i])

        return pkgs

    def install(self):
        run_task(InstallTask(self.get_selected_pkgs(), self._mod))
        self.close()

    def update_deps(self):
        if self._dep_tpl is None:
            self._dep_tpl = self.win.depsLabel.text()

        pkgs = self.get_selected_pkgs()
        all_pkgs = center.settings['mods'].process_pkg_selection(pkgs)
        deps = set(all_pkgs) - set(pkgs)
        names = [pkg.name for pkg in deps if not center.installed.is_installed(pkg)]

        if len(names) == 0:
            self.win.depsLabel.setText('')
        else:
            self.win.depsLabel.setText(self._dep_tpl.replace('{DEPS}', util.human_list(names)))


from .legacy_windows import MainWindow, NebulaWindow