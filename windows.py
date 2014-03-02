import os
import sys
import glob
import util
import clibs
import manager
from six.moves.configparser import ConfigParser
from qt import QtGui
from ui.settings import Ui_Dialog as Ui_Settings


class SettingsWindow(object):
    win = None
    config = None
    mod = None
    
    def __init__(self, mod, app=None):
        if manager.splash is not None:
            parent = manager.splash
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
        # Set default_section to non-existant section to prevent special treatment for the [Default] section.
        self.config = config = ConfigParser(inline_comment_prefixes=(';',), default_section='we_have_no_defaults', interpolation=None)
        
        # Need to set ConfigParser.SafeConfigParser.optionxform() because it completely breaks the case ok FS2 ini keys
        config.optionxform = lambda x: x
        config_file = os.path.expanduser('~/.fs2_open/fs2_open.ini')
        
        # USELESS : win* platforms will do it in a completely different way as this config is stored in the REGISTRY.
        if sys.platform.startswith('win'):
            config_file = os.path.join(manager.settings['fs2_path'], 'data/fs2_open.ini')

        config.read(config_file)

        if not config.has_section('Sound'):
            config.add_section('Sound')
            
        if not config.has_section('Network'):
            config.add_section('Network')

        # video variables
        res_width = None
        res_height = None
        depth = None
        texfilter = None
        af = None
        aa = None

        # sound variables
        playback_device = None
        capture_device = None
        sample_rate = None
        enable_efx = None

        # joystick variable
        joystick_id = None

        # network variables
        net_connection = None
        net_speed = None
        net_ip = None
        net_port = None

        # Check if we already have the config sections:
        if config.has_section('Default'):
            # Be careful with any change, they are all case sensitive.
            # Try to load video settings from the INI file:
            
            if 'VideocardFs2open' in config['Default']:
                rawres = config.get('Default', 'VideocardFs2open')
                res = rawres.split('(')[1].split(')')[0]
                res_width, res_height = res.split('x')
                depth = rawres.split(')x')[1][0:2]
                
                try:
                    res_width = int(res_width)
                    res_height = int(res_height)
                except ValueError:
                    res_width = res_height = None
            
            texfilter = config.get('Default', 'TextureFilter', fallback=None)
            af = config.get('Default', 'OGL_AnisotropicFilter', fallback=None)
            aa = config.get('Default', 'OGL_AntiAliasSamples', fallback=None)
            
            playback_device = config.get('Sound', 'PlaybackDevice', fallback=None)
            capture_device = config.get('Sound', 'CaptureDevice', fallback=None)
            enable_efx = config.get('Sound', 'EnableEFX', fallback=None)
            sample_rate = config.get('Sound', 'SampleRate', fallback=None)
                
            joystick_id = config.get('Default', 'CurrentJoystick', fallback=None)
                
            net_connection = config.get('Default', 'NetworkConnection', fallback=None)
            net_speed = config.get('Default', 'ConnectionSpeed', fallback=None)
            net_port = config.get('Default', 'ForcePort', fallback=None)
            net_ip = config.get('Network', 'CustomIP', fallback=None)

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

        # If the SCP adds a new texture filder, we should change that part
        try:
            index = int(texfilter)
        except ValueError:
            index = 0
        
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
                self.win.snd_playback.addItem(name.decode('utf8'))
            
            index = self.win.snd_playback.findText(playback_device.decode('utf8'))
            if index == -1:
                index = self.win.snd_playback.findText(snd_default.decode('utf8'))
            
            if index != -1:
                self.win.snd_playback.setCurrentIndex(index)
            
            # Fill input device combobox:
            for name in snd_captures:
                self.win.snd_capture.addItem(name.decode('utf8'))
                
            index = self.win.snd_capture.findText(capture_device.decode('utf8'))
            if index == -1:
                index = self.win.snd_capture.findText(snd_default_capture.decode('utf8'))
            
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
            self.win.ctrl_joystick.addItem(joystick.decode('utf8'))

        if util.is_number(joystick_id):
            if joystick_id == '99999':
                self.win.ctrl_joystick.setCurrentIndex(0)
            else:
                self.win.ctrl_joystick.setCurrentIndex(int(joystick_id) + 1)
                if self.win.ctrl_joystick.currentText() == '':
                    self.win.ctrl_joystick.setCurrentIndex(0)
        else:
            self.win.ctrl_joystick.setCurrentIndex(0)

        # Joystick selection disabled for now
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
    
    def update_config(self):
        config = self.config
        
        # Getting ready to write key=value pairs to the ini file
        # Set video
        new_res_width, new_res_height = self.win.vid_res.currentText().split(' (')[0].split(' x ')
        new_depth = self.win.vid_depth.currentText().split('-')[0]
        new_res = 'OGL -({0}x{1})x{2} bit'.format(new_res_width, new_res_height, new_depth)
        config.set('Default', 'VideocardFs2open', new_res)
        
        new_texfilter = str(self.win.vid_texfilter.currentIndex())
        config.set('Default', 'TextureFilter', new_texfilter)
        
        new_aa = self.win.vid_aa.currentText().split('x')[0]
        config.set('Default', 'OGL_AntiAliasSamples', new_aa)
        
        new_af = self.win.vid_af.currentText().split('x')[0]
        config.set('Default', 'OGL_AnisotropicFilter', new_af)
        
        # Set sound :
        new_playback_device = self.win.snd_playback.currentText()
        # ^ wxlauncher uses the same string as CaptureDevice, instead of what openal identifies as the playback device ? Why ?
        # ^ So I do it the way openal is supposed to work, but I'm not sure FS2 really behaves that way
        config.set('Sound', 'PlaybackDevice', new_playback_device)
        config.set('Default', 'SoundDeviceOAL', new_playback_device)
        # ^ Useless according to SCP members, but wxlauncher does it anyway
        
        new_capture_device = self.win.snd_capture.currentText()
        config.set('Sound', 'CaptureDevice', new_capture_device)
        
        if self.win.snd_efx.isChecked() is True:
            new_enable_efx = '1'
        else:
            new_enable_efx = '0'
        config.set('Sound', 'EnableEFX', new_enable_efx)
        
        new_sample_rate = self.win.snd_samplerate.value()
        config.set('Sound', 'SampleRate', new_sample_rate)
        
        # Set joystick
        if self.win.ctrl_joystick.currentText() == 'No Joystick':
            new_joystick_id = '99999'
        else:
            new_joystick_id = str(self.win.ctrl_joystick.currentIndex() - 1)
        config.set('Default', 'CurrentJoystick', new_joystick_id)
        
        # Set networking
        net_types = {0: 'none', 1: 'dialup', 2: 'LAN'}
        new_net_connection = net_types[self.win.net_type.currentIndex()]
        config.set('Default', 'NetworkConnection', new_net_connection)
        
        net_speeds = {0: 'none', 1: 'Slow', 2: '56K', 3: 'ISDN', 4: 'Cable', 5: 'Fast'}
        new_net_speed = net_speeds[self.win.net_speed.currentIndex()]
        config.set('Default', 'ConnectionSpeed', new_net_speed)
        
        new_net_ip = self.win.net_ip.text()
        if new_net_ip == '...':
            new_net_ip = ''
        config.set('Network', 'CustomIP', new_net_ip)
        if config.get('Network', 'CustomIP') == '':
            config.remove_option('Network', 'CustomIP')
        
        new_net_port = self.win.net_port.text()
        if new_net_port == '0':
            new_net_port = ''
        config.set('Default', 'ForcePort', new_net_port)
        if config.get('Default', 'ForcePort') == '':
            config.remove_option('Default', 'ForcePort')
        
        # A bit of cleanup
        if config.items('Sound') == []:
            config.remove_section('Sound')
            
        if config.items('Network') == []:
            config.remove_section('Network')
        
        # TODO: Write

    def run_mod(self):
        if manager.splash is not None:
            manager.splash.show()
        
        self.write_config()
        self.win.close()
        
        if manager.splash is not None:
            manager.splash.label.setText('Launching FS2...')
            manager.signals.fs2_launched.connect(manager.app.quit)
            manager.app.processEvents()
        
        manager.run_mod(self.mod)
