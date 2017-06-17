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
import logging
from collections import OrderedDict

from . import center, util, api, launcher, runner
from .tasks import run_task, CheckTask
from .qt import QtCore, QtWidgets, QtGui


tr = QtCore.QCoreApplication.translate


def get_settings():
    fso = {}

    fs2_bins = OrderedDict()
    fred_bins = OrderedDict()

    for mid, mvs in center.installed.mods.items():
        if mvs[0].mtype == 'engine':
            for v in mvs:
                for pkg in v.packages:
                    for exe in pkg.executables:
                        name = '%s - %s' % (v.title, exe['version'])
                        if exe.get('debug'):
                            name += ' (Debug)'

                        if exe.get('fred'):
                            fred_bins[name] = os.path.join(v.folder, exe['file'])
                        else:
                            fs2_bins[name] = os.path.join(v.folder, exe['file'])

    fso['fs2_bins'] = fs2_bins
    fso['fred_bins'] = fred_bins

    dev_info = get_deviceinfo()

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
    
    # TODO: Implement UUID handling
    if util.is_number(joystick_id):
        if joystick_id == '99999':
            fso['joystick_id'] = 'No Joystick'
        else:
            fso['joystick_id'] = int(joystick_id)
    else:
        fso['joystick_id'] = 'No Joystick'

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
            section['CurrentJoystick'] = new_settings['joystick_id']

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
    except:
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
    config_file = os.path.join(api.get_fso_profile_path(), 'fs2_open.ini')
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
            elif not line.startswith((';', '#')):
                middle = line.find('=')

                if not middle:
                    logging.warning('Invalid line in INI file: %s' % line)
                    continue

                key = line[:middle].strip()
                value = line[middle + 1:].strip()
                current[key] = value

    return sections


def write_fso_config(sections):
    config_file = os.path.join(api.get_fso_profile_path(), 'fs2_open.ini')

    with open(config_file, 'w') as stream:
        for name, pairs in sections.items():
            stream.write('[%s]\n' % name)

            for k, v in pairs.items():
                stream.write('%s = %s\n' % (k, v))

            stream.write('\n')


def get_deviceinfo():
    try:
        info = json.loads(util.check_output(launcher.get_cmd(['--deviceinfo'])).strip())
    except:
        logging.exception('Failed to retrieve device info!')

        QtWidgets.QMessageBox.critical(None, 'Knossos', tr('SettingsWindow',
            'There was an error trying to retrieve your device info (screen resolution, joysticks and audio' +
            ' devices). Please try again or report this error on the HLP thread.'))
        return None

    return info


def test_libs():
    sdl_path = center.settings['sdl2_path']
    oal_path = center.settings['openal_path']

    try:
        info = json.loads(util.check_output(launcher.get_cmd(['--lib-paths', sdl_path, oal_path])).strip())
    except:
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

        if not api.get_fso_flags():
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
            api.enable_raven()
        else:
            api.disable_raven()

    center.settings[name] = value
    api.save_settings()


def get_fso_log(self):
    logpath = os.path.join(api.get_fso_profile_path(), 'data/fs2_open.log')

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
    path = api.get_fso_profile_path()
    QtGui.QDesktopServices.openUrl(QtCore.QUrl('file://' + path))


def clear_hash_cache(self):
    util.HASH_CACHE = dict()
    run_task(CheckTask())
    QtWidgets.QMessageBox.information(None, 'Knossos', tr('SettingsWindow', 'Done!'))
