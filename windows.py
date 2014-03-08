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
import sys
import logging
import glob
import shlex
import stat
import util
import clibs
import manager
from qt import QtCore, QtGui
from ui.settings import Ui_Dialog as Ui_Settings
from ui.flags import Ui_Dialog as Ui_Flags

# Keep references to all open windows to prevent the GC from deleting them.
_open_wins = []


class Window(object):
    win = None
    
    def open(self):
        global _open_wins
        
        _open_wins.append(self)
        self.win.closed.connect(self._del)
        self.win.finished.connect(self._del)
        self.win.show()
    
    def close(self):
        self.win.close()
    
    def _del(self):
        # Make sure all events are processed.
        QtCore.QTimer.singleShot(3, self._del2)
    
    def _del2(self):
        global _open_wins
        
        _open_wins.remove(self)


class SettingsWindow(Window):
    config = None
    mod = None
    _app = None
    
    def __init__(self, mod, app=None):
        if manager.splash is not None:
            parent = manager.splash
            self._app = app
        else:
            parent = manager.main_win
        
        self.mod = mod
        self.win = util.init_ui(Ui_Settings(), util.QDialog(parent))
        self.win.setModal(True)
        
        if mod is None:
            self.win.cmdButton.setText('Default command line flags')
        else:
            self.win.cmdButton.setText('Command line flags for: {0}'.format(mod.name))
        
        self.win.cmdButton.clicked.connect(self.show_flagwin)
        self.read_config()
        
        self.win.runButton.clicked.connect(self.run_mod)
        self.win.cancelButton.clicked.connect(self.win.close)
        
        if manager.splash is not None:
            self.win.destroyed.connect(app.quit)
            manager.splash.hide()
        
        self.open()
    
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
        # This is temporary: it will be better handled as soon as all mods use a default build
        # Binary selection combobox logic here
        fs2_path = manager.settings['fs2_path']

        if fs2_path is not None and os.path.isdir(fs2_path):
            fs2_path = os.path.abspath(fs2_path)
            bins = glob.glob(os.path.join(fs2_path, 'fs2_open_*'))
            
            for i, path in enumerate(bins):
                path = os.path.basename(path)
                self.win.build.addItem(path)
            
            if len(bins) == 1:
                # Found only one binary, select it by default.
                self.win.build.setEnabled(False)

        # ---Read fs2_open.ini or the registry---
        if sys.platform.startswith('win'):
            self.config = config = QtCore.QSettings("HKEY_LOCAL_MACHINE\\Software\\Volition\\Freespace2", QtCore.QSettings.NativeFormat)
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
        raw_modes = clibs.get_modes()
        modes = []
        for mode in raw_modes:
            if mode not in modes and not (mode[0] < 800 or mode[1] < 600):
                modes.append(mode)
        
        for i, (width, height) in enumerate(modes):
            self.win.vid_res.addItem('{0} x {1} ({2})'.format(width, height, self.get_ratio(width, height)))
            
            if width == res_width and height == res_height:
                self.win.vid_res.setCurrentIndex(i)
        
        # Screen depth
        self.win.vid_depth.addItems(['32-bit', '16-bit'])

        index = self.win.vid_depth.findText('{0}-bit'.format(depth))
        if index != -1:
            self.win.vid_depth.setCurrentIndex(index)

        # Texture filter
        self.win.vid_texfilter.addItems(['Bilinear', 'Trilinear'])

        try:
            index = int(texfilter)
        except TypeError:
            index = 0
        
        # If the SCP adds a new texture filder, we should change this part.
        if index > 1:
            index = 0
        self.win.vid_texfilter.setCurrentIndex(index)

        # Antialiasing
        self.win.vid_aa.addItems(['Off', '2x', '4x', '8x', '16x'])

        index = self.win.vid_aa.findText('{0}x'.format(aa))
        if index == -1:
            index = 0
        self.win.vid_aa.setCurrentIndex(index)

        # Anisotropic filtering
        self.win.vid_af.addItems(['Off', '1x', '2x', '4x', '8x', '16x'])

        index = self.win.vid_af.findText('{0}x'.format(af))
        if index == -1:
            index = 0
        self.win.vid_af.setCurrentIndex(index)

        # ---Sound settings---
        if clibs.can_detect_audio():
            snd_devs, snd_default, snd_captures, snd_default_capture = clibs.list_audio_devs()
            
            for name in snd_devs:
                self.win.snd_playback.addItem(name)
            
            if playback_device is not None:
                index = self.win.snd_playback.findText(playback_device)
                if index == -1:
                    index = self.win.snd_playback.findText(snd_default)
            
            if index != -1:
                self.win.snd_playback.setCurrentIndex(index)
            
            # Fill input device combobox:
            for name in snd_captures:
                self.win.snd_capture.addItem(name)
            
            if capture_device is not None:
                index = self.win.snd_capture.findText(capture_device)
                if index == -1:
                    index = self.win.snd_capture.findText(snd_default_capture)
            
            if index != -1:
                self.win.snd_capture.setCurrentIndex(index)
            
            # Fill sample rate textbox :
            self.win.snd_samplerate.setMinimum(0)
            self.win.snd_samplerate.setMaximum(1000000)
            self.win.snd_samplerate.setSingleStep(100)
            self.win.snd_samplerate.setSuffix(' Hz')
            
            if util.is_number(sample_rate):
                sample_rate = int(sample_rate)
                if sample_rate > 0 and sample_rate < 1000000:
                    self.win.snd_samplerate.setValue(sample_rate)
                else:
                    self.win.snd_samplerate.setValue(44100)
            else:
                self.win.snd_samplerate.setValue(44100)
            
            # Fill EFX checkbox :
            if enable_efx == '1':
                self.win.snd_efx.setChecked(True)
            else:
                self.win.snd_efx.setChecked(False)
                 
        # ---Joystick settings---
        joysticks = clibs.list_joysticks()
        
        self.win.ctrl_joystick.addItem('No Joystick')
        for joystick in joysticks:
            self.win.ctrl_joystick.addItem(joystick)

        if util.is_number(joystick_id):
            if joystick_id == '99999':
                self.win.ctrl_joystick.setCurrentIndex(0)
            else:
                self.win.ctrl_joystick.setCurrentIndex(int(joystick_id) + 1)
                if self.win.ctrl_joystick.currentText() == '':
                    self.win.ctrl_joystick.setCurrentIndex(0)
        else:
            self.win.ctrl_joystick.setCurrentIndex(0)

        if len(joysticks) == 0:
            self.win.ctrl_joystick.setEnabled(False)
            
        #---Network settings---

        self.win.net_type.addItems(['None', 'Dialup', 'Broadband/LAN'])
        net_connections_read = {'none': 0, 'dialup': 1, 'LAN': 2}
        if net_connection in net_connections_read:
            index = net_connections_read[net_connection]
        else:
            index = 2
             
        self.win.net_type.setCurrentIndex(index)

        self.win.net_speed.addItems(['None', '28k modem', '56k modem', 'ISDN', 'DSL', 'Cable/LAN'])
        net_speeds_read = {'none': 0, 'Slow': 1, '56K': 2, 'ISDN': 3, 'Cable': 4, 'Fast': 5}
        if net_speed in net_speeds_read:
            index = net_speeds_read[net_speed]
        else:
            index = 5
             
        self.win.net_speed.setCurrentIndex(index)

        self.win.net_ip.setInputMask('000.000.000.000')
        self.win.net_ip.setText(net_ip)

        self.win.net_port.setInputMask('00000')
        self.win.net_port.setText(net_port)
    
    def write_config(self):
        config = self.config
        
        if sys.platform.startswith('win'):
            section = ''
        else:
            config.beginGroup('Default')
            section = 'Default/'
        
        # Getting ready to write key=value pairs to the ini file
        # Set video
        new_res_width, new_res_height = self.win.vid_res.currentText().split(' (')[0].split(' x ')
        new_depth = self.win.vid_depth.currentText().split('-')[0]
        new_res = 'OGL -({0}x{1})x{2} bit'.format(new_res_width, new_res_height, new_depth)
        config.setValue('VideocardFs2open', new_res)
        
        new_texfilter = self.win.vid_texfilter.currentIndex()
        config.setValue('TextureFilter', new_texfilter)
        
        new_aa = self.win.vid_aa.currentText().split('x')[0]
        config.setValue('OGL_AntiAliasSamples', new_aa)
        
        new_af = self.win.vid_af.currentText().split('x')[0]
        config.setValue('OGL_AnisotropicFilter', new_af)
        
        if not sys.platform.startswith('win'):
            config.endGroup()
        
        # sound
        new_playback_device = self.win.snd_playback.currentText()
        # ^ wxlauncher uses the same string as CaptureDevice, instead of what openal identifies as the playback device ? Why ?
        # ^ So I do it the way openal is supposed to work, but I'm not sure FS2 really behaves that way
        config.setValue('Sound/PlaybackDevice', new_playback_device)
        config.setValue(section + 'SoundDeviceOAL', new_playback_device)
        # ^ Useless according to SCP members, but wxlauncher does it anyway
        
        new_capture_device = self.win.snd_capture.currentText()
        config.setValue('Sound/CaptureDevice', new_capture_device)
        
        if self.win.snd_efx.isChecked() is True:
            new_enable_efx = 1
        else:
            new_enable_efx = 0
        config.setValue('Sound/EnableEFX', new_enable_efx)
        
        new_sample_rate = self.win.snd_samplerate.value()
        config.setValue('Sound/SampleRate', new_sample_rate)
        
        # joystick
        if self.win.ctrl_joystick.currentText() == 'No Joystick':
            new_joystick_id = 99999
        else:
            new_joystick_id = self.win.ctrl_joystick.currentIndex() - 1
        config.setValue(section + 'CurrentJoystick', new_joystick_id)
        
        # networking
        net_types = {0: 'none', 1: 'dialup', 2: 'LAN'}
        new_net_connection = net_types[self.win.net_type.currentIndex()]
        config.setValue(section + 'NetworkConnection', new_net_connection)
        
        net_speeds = {0: 'none', 1: 'Slow', 2: '56K', 3: 'ISDN', 4: 'Cable', 5: 'Fast'}
        new_net_speed = net_speeds[self.win.net_speed.currentIndex()]
        config.setValue(section + 'ConnectionSpeed', new_net_speed)
        
        new_net_ip = self.win.net_ip.text()
        if new_net_ip == '...':
            new_net_ip = ''
        
        if new_net_ip == '':
            config.remove('Network/CustomIP')
        else:
            config.setValue('Network/CustomIP', new_net_ip)
        
        new_net_port = self.win.net_port.text()
        if new_net_port == '0':
            new_net_port = ''
        
        if new_net_port == '':
            config.remove(section + 'ForcePort')
        else:
            config.setValue(section + 'ForcePort', int(new_net_port))
        
        # Save the new configuration.
        config.sync()

    def run_mod(self):
        logging.info('Launching...')
        
        if manager.splash is not None:
            manager.splash.show()
        
        self.write_config()
        self.win.close()
        
        if manager.splash is not None:
            manager.splash.label.setText('Launching FS2...')
            manager.signals.fs2_launched.connect(self._app.quit)
            self._app.processEvents()
        
        manager.run_mod(self.mod)
    
    def show_flagwin(self):
        FlagsWindow(self.win, self.mod)


class FlagsWindow(Window):
    _flags = None
    _selected = None
    _mod = None
    
    def __init__(self, parent=None, mod=None):
        super(FlagsWindow, self).__init__()
        
        self._selected = []
        self._mod = mod
        
        self.win = util.init_ui(Ui_Flags(), util.QDialog(parent))
        self.win.setModal(True)
        
        self.win.easySetup.activated.connect(self._set_easy)
        self.win.easySetup.activated.connect(self.update_display)
        self.win.listType.activated.connect(self._update_list)
        self.win.customFlags.textEdited.connect(self.update_display)
        self.win.flagList.itemClicked.connect(self.update_display)
        
        self.win.accepted.connect(self.save)
        
        self.read_flags()
        self.open()
        
        if mod is None or mod.name not in manager.settings['cmdlines']:
            if '#default' in manager.settings['cmdlines']:
                self.set_selection(manager.settings['cmdlines']['#default'])
        else:
            self.set_selection(manager.settings['cmdlines'][mod.name])
    
    def read_flags(self):
        fs2_bin = os.path.join(manager.settings['fs2_path'], manager.settings['fs2_bin'])
        flags_path = os.path.join(manager.settings['fs2_path'], 'flags.lch')
        mode = os.stat(fs2_bin).st_mode
        
        if mode & stat.S_IXUSR != stat.S_IXUSR:
            # Make it executable.
            os.chmod(fs2_bin, mode | stat.S_IXUSR)
        
        # TODO: Shouldn't we cache the flags?
        # Right now FS2 will be called every time this window opens...
        util.call([fs2_bin, '-get_flags'])
        
        if not os.path.isfile(flags_path):
            logging.error('Could not find the flags file "%s"!', flags_path)
            
            self.win.easySetup.setDisabled(True)
            self.win.listType.setDisabled(True)
            self.win.flagList.setDisabled(True)
            return None
        
        with open(flags_path, 'rb') as stream:
            flags = util.FlagsReader(stream)
        
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
        fs2_bin = os.path.join(manager.settings['fs2_path'], manager.settings['fs2_bin'])
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
    
    def save(self):
        if self._mod is None:
            manager.settings['cmdlines']['#default'] = self.get_selection()
        else:
            manager.settings['cmdlines'][self._mod.name] = self.get_selection()
        
        manager.save_settings()
