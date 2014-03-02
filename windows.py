## Copyright 2014 ngld <ngld@tproxy.de>
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
import glob
import logging
import util
import clibs
import manager
from qt import QtCore, QtGui
from ui.settings import Ui_Dialog as Ui_Settings


class SettingsWindow(object):
    win = None
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
        self.win = util.init_ui(Ui_Settings(), QtGui.QDialog(parent))
        self.win.setModal(True)

        self.win.cmdButton.setText('Command line flags for : {0}'.format(mod.name))
        self.read_config()
        
        self.win.runButton.clicked.connect(self.run_mod)
        self.win.cancelButton.clicked.connect(self.win.close)
        
        if manager.splash is not None:
            self.win.destroyed.connect(app.quit)
            manager.splash.hide()
        
        self.win.show()
    
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
        
        # ---Read fs2_open.ini---
        config_file = os.path.expanduser('~/.fs2_open/fs2_open.ini')
        
        # USELESS : win* platforms will do it in a completely different way as this config is stored in the REGISTRY.
        if sys.platform.startswith('win'):
            config_file = os.path.join(manager.settings['fs2_path'], 'data/fs2_open.ini')
        
        self.config = config = QtCore.QSettings(config_file, QtCore.QSettings.IniFormat)
        
        # Be careful with any change, the keys are all case sensitive.
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
        config.beginGroup('Default')
        
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
        
        config.endGroup()
        
        # sound
        new_playback_device = self.win.snd_playback.currentText()
        # ^ wxlauncher uses the same string as CaptureDevice, instead of what openal identifies as the playback device ? Why ?
        # ^ So I do it the way openal is supposed to work, but I'm not sure FS2 really behaves that way
        config.setValue('Sound/PlaybackDevice', new_playback_device)
        config.setValue('Default/SoundDeviceOAL', new_playback_device)
        # ^ Useless according to SCP members, but wxlauncher does it anyway
        
        new_capture_device = self.win.snd_capture.currentText()
        config.setValue('Sound/CaptureDevice', new_capture_device)
        
        if self.win.snd_efx.isChecked() is True:
            new_enable_efx = '1'
        else:
            new_enable_efx = '0'
        config.setValue('Sound/EnableEFX', new_enable_efx)
        
        new_sample_rate = self.win.snd_samplerate.value()
        config.setValue('Sound/SampleRate', new_sample_rate)
        
        # joystick
        if self.win.ctrl_joystick.currentText() == 'No Joystick':
            new_joystick_id = '99999'
        else:
            new_joystick_id = self.win.ctrl_joystick.currentIndex() - 1
        config.setValue('Default/CurrentJoystick', new_joystick_id)
        
        # networking
        net_types = {0: 'none', 1: 'dialup', 2: 'LAN'}
        new_net_connection = net_types[self.win.net_type.currentIndex()]
        config.setValue('Default/NetworkConnection', new_net_connection)
        
        net_speeds = {0: 'none', 1: 'Slow', 2: '56K', 3: 'ISDN', 4: 'Cable', 5: 'Fast'}
        new_net_speed = net_speeds[self.win.net_speed.currentIndex()]
        config.setValue('Default/ConnectionSpeed', new_net_speed)
        
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
            config.remove('Default/ForcePort')
        else:
            config.setValue('Default/ForcePort', new_net_port)
        
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
