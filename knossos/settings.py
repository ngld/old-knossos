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
import json
import struct
import logging
from collections import OrderedDict
from threading import Thread

from . import center, util, launcher, runner
from .tasks import run_task
from .qt import QtCore, QtWidgets, QtGui


tr = QtCore.QCoreApplication.translate


# See code/cmdline/cmdline.cpp (in the SCP source) for details on the data structure.
class FlagsReader(object):
    _stream = None
    easy_flags = None
    flags = None
    build_caps = None

    def __init__(self, stream):
        self._stream = stream
        self.read()

    def unpack(self, fmt):
        if isinstance(fmt, struct.Struct):
            return fmt.unpack(self._stream.read(fmt.size))
        else:
            return struct.unpack(fmt, self._stream.read(struct.calcsize(fmt)))

    def read(self):
        # Explanation of unpack() and Struct() parameters: http://docs.python.org/3/library/struct.html#format-characters
        self.easy_flags = OrderedDict()
        self.flags = OrderedDict()

        easy_size, flag_size = self.unpack('2i')

        easy_struct = struct.Struct('32s')
        flag_struct = struct.Struct('20s40s?ii16s256s')

        if easy_size != easy_struct.size:
            logging.error('EasyFlags size is %d but I expected %d!', easy_size, easy_struct.size)
            return

        if flag_size != flag_struct.size:
            logging.error('Flag size is %d but I expected %d!', flag_size, flag_struct.size)
            return

        for i in range(self.unpack('i')[0]):
            self.easy_flags[1 << i] = self.unpack(easy_struct)[0].decode('utf8').strip('\x00')

        for i in range(self.unpack('i')[0]):
            flag = self.unpack(flag_struct)
            flag = {
                'name': flag[0].decode('utf8').strip('\x00'),
                'desc': flag[1].decode('utf8').strip('\x00'),
                'fso_only': flag[2],
                'on_flags': flag[3],
                'off_flags': flag[4],
                'type': flag[5].decode('utf8').strip('\x00'),
                'web_url': flag[6].decode('utf8').strip('\x00')
            }

            if flag['type'] not in self.flags:
                self.flags[flag['type']] = []

            self.flags[flag['type']].append(flag)

        self.build_caps = self.unpack('b')[0]

    @property
    def openal(self):
        return self.build_caps & 1

    @property
    def no_d3d(self):
        return self.build_caps & (1 << 1)

    @property
    def new_snd(self):
        return self.build_caps & (1 << 2)

    @property
    def sdl(self):
        return self.build_caps & (1 << 3)

    def to_dict(self):
        return {
            'easy_flags': self.easy_flags,
            'flags': self.flags,
            'openal': self.openal,
            'no_d3d': self.no_d3d,
            'new_snd': self.new_snd,
            'sdl': self.sdl
        }


def get_settings(cb):
    def wrapper():
        cb(get_settings_p2())

    t = Thread(target=wrapper)
    t.start()


def get_settings_p2():
    dev_info = get_deviceinfo()
    fso = {}

    # ---Read fs2_open.ini or the registry---
    # Be careful with any change, the keys are all case sensitive.
    config = parse_fso_config()
    section = config.get('Default', {})

    # video settings
    if 'VideocardFs2open' in section:
        rawres = section['VideocardFs2open']

        try:
            res = rawres.split('(')[1].split(')')[0]
            res_width, res_height = res.split('x')
            depth = rawres.split(')x')[1][0:2]

            res_width = int(res_width)
            res_height = int(res_height)
        except (TypeError, IndexError):
            res_width = res_height = None
    else:
        res_width = None
        res_height = None
        depth = '32'

    texfilter = section.get('TextureFilter', '1')
    # af = section.get('OGL_AnisotropicFilter', None)
    # aa = section.get('OGL_AntiAliasSamples', None)

    # joysticks
    joystick_id = section.get('CurrentJoystick', None)
    joystick_enable_hit = section.get('EnableHitEffect', False)
    joystick_ff_strength = config.get('ForceFeedback', {}).get('Strength', 100)

    # speech
    speech_vol = section.get('SpeechVolume', 100)
    speech_voice = section.get('SpeechVoice', 0)
    speech_techroom = section.get('SpeechTechroom', 0)
    speech_briefings = section.get('SpeechBriefings', 0)
    speech_ingame = section.get('SpeechIngame', 0)
    speech_multi = section.get('SpeechMulti', 0)

    # network settings
    net_connection = section.get('NetworkConnection', None)
    net_speed = section.get('ConnectionSpeed', None)
    net_port = section.get('ForcePort', None)

    net_ip = section.get('Network/CustomIP', None)

    section = config.get('Sound', {})

    # sound settings
    playback_device = section.get('PlaybackDevice', None)
    capture_device = section.get('CaptureDevice', None)
    enable_efx = section.get('EnableEFX', None)
    sample_rate = section.get('SampleRate', 44100)

    # ---Video settings---
    # Screen resolution
    modes = []
    if dev_info:
        for w, h in dev_info['modes']:
            if w > 800 and h > 600:
                modes.append('{0} x {1} ({2})'.format(w, h, get_ratio(w, h)))

    fso['modes'] = modes
    fso['depth'] = depth

    if res_width and res_height:
        fso['active_mode'] = '{0} x {1} ({2})'.format(res_width, res_height, get_ratio(res_width, res_height))
    elif len(modes) > 0:
        fso['active_mode'] = modes[0]
    else:
        fso['active_mode'] = ''

    try:
        index = int(texfilter)
    except TypeError:
        index = 0

    # If the SCP adds a new texture filder, we should change this part.
    if index > 1:
        index = 0
    fso['texfilter'] = index

    # ---Sound settings---
    if dev_info and dev_info['audio_devs']:
        snd_devs, snd_default, snd_captures, snd_default_capture = dev_info['audio_devs']

        if not playback_device and len(snd_devs) > 0:
            playback_device = snd_devs[0]

        if not capture_device and len(snd_captures) > 0:
            capture_device = snd_captures[0]

        fso['audio_devs'] = snd_devs
        fso['active_audio_dev'] = playback_device
        fso['default_audio_dev'] = snd_default

        fso['cap_devs'] = snd_captures
        fso['active_cap_dev'] = capture_device
        fso['default_cap_dev'] = snd_default_capture

        if util.is_number(sample_rate):
            sample_rate = int(sample_rate)
            if sample_rate > 0 and sample_rate < 1000000:
                fso['sample_rate'] = sample_rate
            else:
                fso['sample_rate'] = 44100
        else:
            fso['sample_rate'] = 44100

        # Fill EFX checkbox :
        fso['enable_efx'] = enable_efx == '1'

    # ---Joystick settings---
    fso['joysticks'] = dev_info['joysticks'] if dev_info else []
    fso['joystick_enable_hit'] = joystick_enable_hit == '1'
    fso['joystick_ff_strength'] = joystick_ff_strength

    # TODO: Implement UUID handling
    if util.is_number(joystick_id):
        if joystick_id == '99999':
            fso['joystick_id'] = 'No Joystick'
        else:
            fso['joystick_id'] = int(joystick_id)
    else:
        fso['joystick_id'] = 'No Joystick'

    # Speech
    fso['speech_vol'] = speech_vol
    fso['speech_voice'] = speech_voice
    fso['voice_list'] = dev_info['voices']

    fso['speech_techroom'] = speech_techroom == '1'
    fso['speech_briefings'] = speech_briefings == '1'
    fso['speech_ingame'] = speech_ingame == '1'
    fso['speech_multi'] = speech_multi == '1'

    # ---Network settings---
    net_connections_read = {'none': 0, 'dialup': 1, 'LAN': 2}
    if net_connection in net_connections_read:
        index = net_connections_read[net_connection]
    else:
        index = 2

    fso['net_type'] = index

    net_speeds_read = {'none': 0, 'Slow': 1, '56K': 2, 'ISDN': 3, 'Cable': 4, 'Fast': 5}
    if net_speed in net_speeds_read:
        index = net_speeds_read[net_speed]
    else:
        index = 5

    fso['net_speed'] = index
    fso['net_ip'] = net_ip
    fso['net_port'] = net_port

    kn_settings = center.settings.copy()
    del kn_settings['hash_cache']

    fso['has_voice'] = sys.platform == 'win32'

    return {
        'knossos': kn_settings,
        'languages': center.LANGUAGES,
        'has_log': launcher.log_path is not None,
        'fso': fso
    }


def save_fso_settings(new_settings):
    config = parse_fso_config()

    try:
        section = config.setdefault('Default', {})

        # Getting ready to write key=value pairs to the ini file
        # Set video
        new_res_width, new_res_height = new_settings['active_mode'].split(' (')[0].split(' x ')
        new_depth = new_settings['depth']

        section['VideocardFs2open'] = 'OGL -({0}x{1})x{2} bit'.format(new_res_width, new_res_height, new_depth)
        section['TextureFilter'] = new_settings['texfilter']

        # section['OGL_AntiAliasSamples'] = new_aa
        # section['OGL_AnisotropicFilter'] = new_af

        # sound
        section = config.setdefault('Sound', {})

        section['PlaybackDevice'] = new_settings.get('active_audio_dev', '')
        # ^ wxlauncher uses the same string as CaptureDevice, instead of what openal identifies as the playback device.
        # ^ So I do it the way openal is supposed to work, but I'm not sure FS2 really behaves that way

        section['CaptureDevice'] = new_settings.get('active_cap_dev', '')

        if new_settings['enable_efx']:
            section['EnableEFX'] = 1
        else:
            section['EnableEFX'] = 0

        section['SampleRate'] = new_settings['sample_rate']

        section = config['Default']

        # joystick
        if new_settings.get('joystick_id', 'No Joystick') == 'No Joystick':
            section['CurrentJoystick'] = 99999
        else:
            section['CurrentJoystickGUID'] = new_settings['joystick_id']

        section['EnableHitEffect'] = 1 if new_settings['joystick_enable_hit'] else 0
        config['ForceFeedback'] = {'Strength': new_settings['joystick_ff_strength']}

        # Speech
        section['SpeechVolume'] = new_settings['speech_vol']
        section['SpeechVoice'] = new_settings['speech_voice']

        section['SpeechTechroom'] = 1 if new_settings['speech_techroom'] else 0
        section['SpeechBriefings'] = 1 if new_settings['speech_briefings'] else 0
        section['SpeechIngame'] = 1 if new_settings['speech_ingame'] else 0
        section['SpeechMulti'] = 1 if new_settings['speech_multi'] else 0

        # networking
        # net_types = {0: 'none', 1: 'dialup', 2: 'LAN'}
        # new_net_connection = net_types[self._tabs['fso_network'].connectionType.currentIndex()]
        # section['NetworkConnection'] = new_net_connection

        # net_speeds = {0: 'none', 1: 'Slow', 2: '56K', 3: 'ISDN', 4: 'Cable', 5: 'Fast'}
        # new_net_speed = net_speeds[self._tabs['fso_network'].connectionSpeed.currentIndex()]
        # section['ConnectionSpeed'] = new_net_speed

        # new_net_ip = self._tabs['fso_network'].forceAddress.text()
        # if new_net_ip == '...':
        #     new_net_ip = ''

        # if new_net_ip == '':
        #     config.remove('Network/CustomIP')
        # else:
        #     config.setValue('Network/CustomIP'] = new_net_ip

        # new_net_port = self._tabs['fso_network'].localPort.text()
        # if new_net_port == '0':
        #     new_net_port = ''
        # elif new_net_port != '':
        #     try:
        #         new_net_port = int(new_net_port)
        #     except ValueError:
        #         new_net_port = ''

        # if new_net_port == '':
        #     config.remove(section + 'ForcePort')
        # else:
        #     section['ForcePort'] = new_net_port

        # Save the new configuration.
        write_fso_config(config)
    except Exception:
        logging.exception('Failed to save the configuration!')
        QtWidgets.QMessageBox.critical(None, 'Knossos', tr('SettingsWindow', 'Failed to save the configuration!'))


def get_ratio(w, h):
    try:
        w = int(w)
        h = int(h)
    except TypeError:
        return '?'

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


def parse_fso_config():
    config_file = os.path.join(get_fso_profile_path(), 'fs2_open.ini')
    if not os.path.isfile(config_file):
        return {}

    sections = {}
    current = None
    with open(config_file, 'r') as stream:
        for line in stream:
            if line.startswith('['):
                end = line.find(']')
                if not end:
                    logging.warning('Invalid line in INI file: %s' % line)
                    continue

                name = line[1:end]
                sections[name] = current = {}
            elif not line.startswith((';', '#')) and line.strip() != '':
                middle = line.find('=')

                if not middle:
                    logging.warning('Invalid line in INI file: %s' % line)
                    continue

                key = line[:middle].strip()
                value = line[middle + 1:].strip()
                current[key] = value

    return sections


def write_fso_config(sections):
    config_file = os.path.join(get_fso_profile_path(), 'fs2_open.ini')

    with open(config_file, 'w') as stream:
        for name, pairs in sections.items():
            stream.write('[%s]\n' % name)

            for k, v in pairs.items():
                stream.write('%s = %s\n' % (k, v))

            stream.write('\n')


def ensure_fso_config():
    config_file = os.path.join(get_fso_profile_path(), 'fs2_open.ini')
    if not os.path.isfile(config_file):
        settings = get_settings_p2()
        save_fso_settings(settings['fso'])


def get_deviceinfo():
    from knossos import clibs

    clibs.init_sdl()
    clibs.init_openal()

    if clibs.can_detect_audio():
        audio_devs = clibs.list_audio_devs()
    else:
        audio_devs = None

    return {
        'modes': clibs.get_modes(),
        'audio_devs': audio_devs,
        'joysticks': clibs.list_joysticks(),
        'voices': clibs.list_voices()
    }


_flag_cache = {}
def get_fso_flags(fs2_bin):
    global fso_flags

    if not os.path.isfile(fs2_bin):
        logging.warning('Tried to get flags for missing executable "%s"!' % fs2_bin)
        return None

    if fs2_bin in _flag_cache:
        mtime, flags = _flag_cache[fs2_bin]

        st = os.stat(fs2_bin)
        if st.st_mtime == mtime:
            return flags

    flags_path = os.path.join(center.settings['base_path'], 'flags.lch')
    rc = runner.run_fs2_silent([fs2_bin, '-get_flags', '-parse_cmdline_only'])

    flags = None

    if rc != 1 and rc != 0:
        logging.error('Failed to run FSO! (Exit code was %d)', rc)
    elif not os.path.isfile(flags_path):
        logging.error('Could not find the flags file "%s"!', flags_path)
    else:
        with open(flags_path, 'rb') as stream:
            flags = FlagsReader(stream)

    st = os.stat(fs2_bin)
    _flag_cache[fs2_bin] = (st.st_mtime, flags)
    return flags


_profile_path = None
def get_fso_profile_path():
    global _profile_path

    if _profile_path is None:
        from knossos import clibs

        clibs.init_sdl()

        return clibs.get_config_path()

    return _profile_path


def test_libs():
    sdl_path = center.settings['sdl2_path']
    oal_path = center.settings['openal_path']

    try:
        info = json.loads(util.check_output(launcher.get_cmd(['--lib-paths', sdl_path, oal_path])).strip())
    except Exception:
        QtWidgets.QMessageBox.critical(None, 'Knossos',
            tr('SettingsWindow', 'An unknown error (a crash?) occurred while trying to load the libraries!'))
    else:
        if info['sdl2'] and info['openal']:
            msg = tr('SettingsWindow', 'Success! Both libraries were loaded successfully.')
        else:
            msg = tr('SettingsWindow', 'Error! One or both libraries failed to load.')

        msg += '\n\nSDL2: %s\nOpenAL: %s' % (
            info['sdl2'] if info['sdl2'] else tr('SettingsWindow', 'Not found'),
            info['openal'] if info['openal'] else tr('SettingsWindow', 'Not found')
        )
        QtWidgets.QMessageBox.information(None, 'Knossos', msg)


def save_setting(name, value):
    if name not in center.settings:
        raise Exception('Trying to set invalid setting "%s"!' % name)

    if name == 'max_downloads':
        if value != center.settings['max_downloads']:
            util.DL_POOL.set_capacity(value)
    if name == 'download_bandwidth':
        if value > 0.0:
            util.SPEED_LIMIT_BUCKET.set_rate(value)
    elif name == 'language':
        # NOTE: This is deliberately not translated.
        QtWidgets.QMessageBox.information(None, 'Knossos', 'Please restart Knossos to complete the language change.')
    elif name == 'fs2_bin':
        path = os.path.join(center.settings['base_path'], 'bin', value)
        if not os.path.isfile(path):
            logging.warning('Tried to set a fs2_bin to a non-existing path: %s' % value)
            return

        old_bin = center.settings['fs2_bin']
        center.settings['fs2_bin'] = value

        if not get_fso_flags(value):
            # We failed to run FSO but why?
            rc = runner.run_fs2_silent(['-help'])
            if rc == -128:
                msg = tr('SettingsWindow', 'The FSO binary "%s" is missing!') % value
            elif rc == -127:
                # TODO: At this point we have run ldd twice already and the next call will run it again.
                # Is there any way to avoid this?
                _, missing = runner.fix_missing_libs(os.path.join(center.settings['base_path'], 'bin', value))
                msg = tr('SettingsWindow', 'The FSO binary "%s" is missing %s!') % (value, util.human_list(missing))
            else:
                msg = tr('SettingsWindow', 'The FSO binary quit with code %d!') % rc

            center.settings['fs2_bin'] = old_bin
            QtWidgets.QMessageBox.critical(None, 'Knossos', msg)
            return
        else:
            center.signals.fs2_bin_changed.emit()
    elif name == 'fred_bin':
        path = os.path.join(center.settings['base_path'], value)
        if not os.path.isfile(path):
            logging.warning('Tried to set a fred_bin to a non-existing path: %s' % value)
            return
    elif name == 'use_raven':
        if value:
            util.enable_raven()
        else:
            util.disable_raven()

    center.settings[name] = value
    center.save_settings()


def get_fso_log(self):
    logpath = os.path.join(get_fso_profile_path(), 'data/fs2_open.log')

    if not os.path.isfile(logpath):
        QtWidgets.QMessageBox.warning(None, 'Knossos',
            tr('SettingsWindow', 'Sorry, but I can\'t find the fs2_open.log file.\nDid you run the debug build?'))
    else:
        with open(logpath, 'r') as hdl:
            return logpath, hdl.read()


def get_knossos_log(self):
    with open(launcher.log_path, 'r') as hdl:
        return launcher.log_path, hdl.read()


def show_fso_cfg_folder(self):
    path = get_fso_profile_path()
    QtGui.QDesktopServices.openUrl(QtCore.QUrl('file://' + path))
