from .ui.add_repo import Ui_AddRepoDialog
from .ui.settings2 import Ui_SettingsDialog
from .ui.settings_about import Ui_AboutForm
from .ui.settings_sources import Ui_ModSourcesForm
from .ui.settings_libs import Ui_LibPathForm
from .ui.settings_knossos import Ui_KnossosSettingsForm
from .ui.settings_fso import Ui_FsoSettingsForm
from .ui.settings_video import Ui_VideoSettingsForm
from .ui.settings_audio import Ui_AudioSettingsForm
from .ui.settings_input import Ui_InputSettingsForm
from .ui.settings_network import Ui_NetworkSettingsForm
from .ui.settings_help import Ui_HelpForm

class SettingsWindow(Window):
    _tabs = None
    _builds = None

    def __init__(self):
        self._tabs = {}
        self._create_win(Ui_SettingsDialog)

        # We're using the dialog's name as the context here because we want the translations to match.
        self._label_lookup = {
            translate('SettingsDialog', 'About Knossos'): 'about',
            translate('SettingsDialog', 'Launcher settings'): 'kn_settings',
            translate('SettingsDialog', 'Retail install'): 'retail_install',
            translate('SettingsDialog', 'Mod sources'): 'mod_sources',
            translate('SettingsDialog', 'Library paths'): 'lib_paths',
            translate('SettingsDialog', 'Game settings'): 'fso_settings',
            translate('SettingsDialog', 'Video'): 'fso_video',
            translate('SettingsDialog', 'Audio'): 'fso_audio',
            translate('SettingsDialog', 'Input'): 'fso_input',
            translate('SettingsDialog', 'Network'): 'fso_network',
            translate('SettingsDialog', 'Default flags'): 'fso_flags',
            translate('SettingsDialog', 'Help'): 'help'
        }

        self.win.treeWidget.expandAll()
        self.win.treeWidget.currentItemChanged.connect(self.select_tab)
        self.win.saveButton.clicked.connect(self.write_config)

        self._tabs['about'] = tab = util.init_ui(Ui_AboutForm(), QtWidgets.QWidget())

        self._tabs['kn_settings'] = tab = util.init_ui(Ui_KnossosSettingsForm(), QtWidgets.QWidget())
        tab.versionLabel.setText(center.VERSION)

        for key, lang in center.LANGUAGES.items():
            tab.langSelect.addItem(lang, QtCore.QVariant(key))

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

        tab.langSelect.currentIndexChanged.connect(self.save_language)
        tab.maxDownloads.valueChanged.connect(self.update_max_downloads)
        tab.updateChannel.currentIndexChanged.connect(self.save_update_settings)
        tab.updateNotify.stateChanged.connect(self.save_update_settings)
        tab.reportErrors.stateChanged.connect(self.save_report_settings)

        self._tabs['retail_install'] = tab = GogExtractWindow(False)
        tab.win.cancelButton.hide()

        self._tabs['mod_sources'] = tab = util.init_ui(Ui_ModSourcesForm(), QtWidgets.QWidget())
        tab.addSource.clicked.connect(self.add_repo)
        tab.editSource.clicked.connect(self.edit_repo)
        tab.removeSource.clicked.connect(self.remove_repo)
        tab.sourceList.itemDoubleClicked.connect(self.edit_repo)

        self._tabs['lib_paths'] = tab = util.init_ui(Ui_LibPathForm(), QtWidgets.QWidget())
        if center.settings['sdl2_path']:
            tab.sdlPath.setText(center.settings['sdl2_path'])
        else:
            tab.sdlPath.setText('auto')

        if center.settings['openal_path']:
            tab.openAlPath.setText(center.settings['openal_path'])
        else:
            tab.openAlPath.setText('auto')

        tab.sdlBtn.clicked.connect(functools.partial(self.select_path, tab.sdlPath))
        tab.openAlBtn.clicked.connect(functools.partial(self.select_path, tab.openAlPath))
        tab.testBtn.clicked.connect(self.test_libs)

        self._tabs['fso_settings'] = tab = util.init_ui(Ui_FsoSettingsForm(), QtWidgets.QWidget())
        tab.browseButton.clicked.connect(self.select_fs2_path)
        tab.build.activated.connect(self.save_build)
        tab.fredBuild.activated.connect(self.save_fred_build)
        tab.openLog.clicked.connect(self.show_fso_log)
        tab.openConfigFolder.clicked.connect(self.show_fso_cfg_folder)

        self._tabs['fso_video'] = tab = util.init_ui(Ui_VideoSettingsForm(), QtWidgets.QWidget())
        self._tabs['fso_audio'] = tab = util.init_ui(Ui_AudioSettingsForm(), QtWidgets.QWidget())
        self._tabs['fso_input'] = tab = util.init_ui(Ui_InputSettingsForm(), QtWidgets.QWidget())
        self._tabs['fso_network'] = tab = util.init_ui(Ui_NetworkSettingsForm(), QtWidgets.QWidget())

        self._tabs['fso_flags'] = tab = FlagsWindow(window=False)
        if center.settings['fs2_path'] is None:
            tab.win.setEnabled(False)

        self._tabs['help'] = util.init_ui(Ui_HelpForm(), QtWidgets.QWidget())

        center.signals.fs2_path_changed.connect(self.read_config)
        center.signals.fs2_bin_changed.connect(tab.read_flags)

        try:
            self.update_repo_list()
            self.read_config()
        except:
            logging.exception('Failed to read the configuration!')
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('The current configuration could not be read!'))

        self.show_tab('about')
        self.open()

    def _del(self):
        center.signals.fs2_path_changed.disconnect(self.read_config)
        center.signals.fs2_bin_changed.disconnect(self._tabs['fso_flags'].read_flags)

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
        self.show_tab(self._label_lookup[item.text(0)])

    def update_repo_list(self):
        tab = self._tabs['mod_sources']
        tab.sourceList.clear()

        for i, r in enumerate(center.settings['repos']):
            item = QtWidgets.QListWidgetItem(r[1], tab.sourceList)
            item.setData(QtCore.Qt.UserRole, i)

    def _edit_repo(self, repo_=None, idx=None):
        win = util.init_ui(Ui_AddRepoDialog(), QDialog(self.win))
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
                        QtWidgets.QMessageBox.critical(self.win, self.tr('Error'),
                            self.tr('This source is already in the list! (As "%s")') % (r_title))
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
        tab = self._tabs['mod_sources']
        item = tab.sourceList.currentItem()
        if item is not None:
            idx = item.data(QtCore.Qt.UserRole)
            self._edit_repo(center.settings['repos'][idx], idx)

    def remove_repo(self):
        tab = self._tabs['mod_sources']
        item = tab.sourceList.currentItem()
        if item is not None:
            idx = item.data(QtCore.Qt.UserRole)
            answer = QtWidgets.QMessageBox.question(self.win, self.tr('Are you sure?'),
                self.tr('Do you really want to remove "%s"?') % (item.text()),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

            if answer == QtWidgets.QMessageBox.Yes:
                del center.settings['repos'][idx]

                api.save_settings()
                self.update_repo_list()

    def reorder_repos(self, parent, s_start, s_end, d_parent, d_row):
        tab = self._tabs['mod_sources']
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
        center.settings['max_downloads'] = num = self._tabs['kn_settings'].maxDownloads.value()

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
    def _get_config():
        config_file = os.path.join(api.get_fso_profile_path(), 'fs2_open.ini')
        if not sys.platform.startswith('win') or os.path.isfile(config_file):
            config = QtCore.QSettings(config_file, QtCore.QSettings.IniFormat)
            config.beginGroup('Default')
            return config, False
        else:
            config = QtCore.QSettings(r'HKEY_LOCAL_MACHINE\Software\Volition\Freespace2', QtCore.QSettings.NativeFormat)
            return config, True

    @classmethod
    def has_config(cls):
        return cls._get_config()[0].contains('VideocardFs2open')

    def get_deviceinfo(self):
        try:
            info = json.loads(util.check_output(launcher.get_cmd(['--deviceinfo'])).strip())
        except:
            logging.exception('Failed to retrieve device info!')

            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr(
                'There was an error trying to retrieve your device info (screen resolution, joysticks and audio' +
                ' devices). Please try again or report this error on the HLP thread.'))
            return None

        return info

    def test_libs(self):
        tab = self._tabs['lib_paths']
        sdl_path = tab.sdlPath.text()
        oal_path = tab.openAlPath.text()

        try:
            info = json.loads(util.check_output(launcher.get_cmd(['--lib-paths', sdl_path, oal_path])).strip())
        except:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr('An unkown error (a crash?) occurred while trying to load the libraries!'))
        else:
            if info['sdl2'] and info['openal']:
                msg = self.tr('Success! Both libraries were loaded successfully.')
            else:
                msg = self.tr('Error! One or both libraries failed to load.')

            msg += '\n\nSDL2: %s\nOpenAL: %s' % (
                info['sdl2'] if info['sdl2'] else self.tr('Not found'),
                info['openal'] if info['openal'] else self.tr('Not found')
            )
            QtWidgets.QMessageBox.information(None, 'Knossos', msg)

    def select_path(self, edit):
        path = QtWidgets.QFileDialog.getOpenFileName(self.win, None, None)[0]

        if path is not None and path != '':
            if not os.path.isfile(path):
                QtWidgets.QMessageBox.critical(self.win, self.tr('Not a file'),
                    self.tr('Please select a proper file'))
                return

            edit.setText(os.path.abspath(path))

    def read_config(self):
        fs2_path = center.settings['fs2_path']
        fs2_bin = center.settings['fs2_bin']
        fred_bin = center.settings['fred_bin']

        tab = self._tabs['fso_settings']
        tab.fs2PathLabel.setText(fs2_path)
        tab.build.clear()

        if fs2_path is not None:
            bins = api.get_executables()
            self._builds = []
            self._fred_builds = []

            idx = 0
            fred_idx = 0
            for name, path in bins:
                if 'fred2' in name:
                    self._fred_builds.append((name, path))
                    tab.fredBuild.addItem(name)

                    if path == fred_bin:
                        tab.fredBuild.setCurrentIndex(fred_idx)

                    fred_idx += 1
                else:
                    self._builds.append((name, path))
                    tab.build.addItem(name)

                    if path == fs2_bin:
                        tab.build.setCurrentIndex(idx)

                    idx += 1

            del idx, fred_idx

            if len(self._builds) < 2:
                tab.build.setEnabled(False)

                if len(self._builds) == 1:
                    # Found only one binary, select it by default.
                    self.save_build()
                else:
                    tab.build.addItem(self.tr('No executable found!'))

            if len(self._fred_builds) < 2:
                tab.fredBuild.setEnabled(False)

                if len(self._fred_builds) == 1:
                    self.save_fred_build()
                else:
                    tab.fredBuild.addItem(self.tr('No executable found!'))

        dev_info = self.get_deviceinfo()

        # ---Read fs2_open.ini or the registry---
        # Be careful with any change, the keys are all case sensitive.
        self.config, self.config_legacy = self._get_config()
        config = self.config

        # video settings
        if config.contains('VideocardFs2open'):
            rawres = config.value('VideocardFs2open')

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
        vid_res = self._tabs['fso_video'].resolution
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
        vid_depth = self._tabs['fso_video'].colorDepth
        vid_depth.clear()
        vid_depth.addItems(['32-bit', '16-bit'])

        index = vid_depth.findText('{0}-bit'.format(depth))
        if index != -1:
            vid_depth.setCurrentIndex(index)

        # Texture filter
        vid_texfilter = self._tabs['fso_video'].textureFilter
        vid_texfilter.clear()
        vid_texfilter.addItems([self.tr('Bilinear'), self.tr('Trilinear')])

        try:
            index = int(texfilter)
        except TypeError:
            index = 0

        # If the SCP adds a new texture filder, we should change this part.
        if index > 1:
            index = 0
        vid_texfilter.setCurrentIndex(index)

        # Antialiasing
        vid_aa = self._tabs['fso_video'].antialiasing
        vid_aa.clear()
        vid_aa.addItems([self.tr('Off'), '2x', '4x', '8x', '16x'])

        index = vid_aa.findText('{0}x'.format(aa))
        if index == -1:
            index = 0
        vid_aa.setCurrentIndex(index)

        # Anisotropic filtering
        vid_af = self._tabs['fso_video'].anisotropic
        vid_af.clear()
        vid_af.addItems([self.tr('Off'), '1x', '2x', '4x', '8x', '16x'])

        index = vid_af.findText('{0}x'.format(af))
        if index == -1:
            index = 0
        vid_af.setCurrentIndex(index)

        # ---Sound settings---
        if dev_info and dev_info['audio_devs']:
            snd_devs, snd_default, snd_captures, snd_default_capture = dev_info['audio_devs']
            snd_playback = self._tabs['fso_audio'].playbackDevice
            snd_capture = self._tabs['fso_audio'].captureDevice
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
            snd_samplerate = self._tabs['fso_audio'].sampleRate
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
                self._tabs['fso_audio'].enableEFX.setChecked(True)
            else:
                self._tabs['fso_audio'].enableEFX.setChecked(False)

        # ---Joystick settings---
        joysticks = dev_info['joysticks'] if dev_info else []
        ctrl_joystick = self._tabs['fso_input'].controller

        ctrl_joystick.clear()
        ctrl_joystick.addItem(self.tr('No Joystick'))
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
        kls = self._tabs['fso_input'].keyLayout
        if sys.platform.startswith('linux'):
            kls.clear()
            for i, layout in enumerate(('default (qwerty)', 'qwertz', 'azerty')):
                kls.addItem(layout)
                if layout == center.settings['keyboard_layout']:
                    kls.setCurrentIndex(i)

            if center.settings['keyboard_setxkbmap']:
                self._tabs['fso_input'].useSetxkbmap.setChecked(True)
            else:
                self._tabs['fso_input'].useSetxkbmap.setChecked(False)
        else:
            kls.setDisabled(True)
            self._tabs['fso_input'].useSetxkbmap.setDisabled(True)

        # ---Network settings---
        net_type = self._tabs['fso_network'].connectionType
        net_speed = self._tabs['fso_network'].connectionSpeed
        net_ip_f = self._tabs['fso_network'].forceAddress
        net_port_f = self._tabs['fso_network'].localPort

        net_type.clear()
        net_type.addItems([self.tr('None'), self.tr('Dialup'), self.tr('Broadband/LAN')])
        net_connections_read = {'none': 0, 'dialup': 1, 'LAN': 2}
        if net_connection in net_connections_read:
            index = net_connections_read[net_connection]
        else:
            index = 2

        net_type.setCurrentIndex(index)

        net_speed.clear()
        net_speed.addItems([self.tr('None'), self.tr('28k modem'), self.tr('56k modem'),
            self.tr('ISDN'), self.tr('DSL'), self.tr('Cable/LAN')])
        net_speeds_read = {'none': 0, 'Slow': 1, '56K': 2, 'ISDN': 3, 'Cable': 4, 'Fast': 5}
        if net_speed in net_speeds_read:
            index = net_speeds_read[net_speed]
        else:
            index = 5

        if isinstance(net_port, int):
            net_port = str(net_port)

        net_speed.setCurrentIndex(index)
        net_ip_f.setText(net_ip)
        net_port_f.setText(net_port)

    def write_config(self):
        config = self.config

        if self.config_legacy:
            section = ''
        else:
            config.beginGroup('Default')
            section = 'Default/'

        try:
            # Getting ready to write key=value pairs to the ini file
            # Set video
            new_res_width, new_res_height = self._tabs['fso_video'].resolution.currentText().split(' (')[0].split(' x ')
            new_depth = self._tabs['fso_video'].colorDepth.currentText().split('-')[0]
            new_res = 'OGL -({0}x{1})x{2} bit'.format(new_res_width, new_res_height, new_depth)
            config.setValue('VideocardFs2open', new_res)

            new_texfilter = self._tabs['fso_video'].textureFilter.currentIndex()
            config.setValue('TextureFilter', new_texfilter)

            new_aa = self._tabs['fso_video'].antialiasing.currentText().split('x')[0]
            config.setValue('OGL_AntiAliasSamples', new_aa)

            new_af = self._tabs['fso_video'].anisotropic.currentText().split('x')[0]
            config.setValue('OGL_AnisotropicFilter', new_af)

            if not sys.platform.startswith('win'):
                config.endGroup()

            # sound
            new_playback_device = self._tabs['fso_audio'].playbackDevice.currentText()
            # ^ wxlauncher uses the same string as CaptureDevice, instead of what openal identifies as the playback device.
            # ^ So I do it the way openal is supposed to work, but I'm not sure FS2 really behaves that way
            config.setValue('Sound/PlaybackDevice', new_playback_device)
            config.setValue(section + 'SoundDeviceOAL', new_playback_device)
            # ^ Useless according to SCP members, but wxlauncher does it anyway

            new_capture_device = self._tabs['fso_audio'].captureDevice.currentText()
            config.setValue('Sound/CaptureDevice', new_capture_device)

            if self._tabs['fso_audio'].enableEFX.isChecked() is True:
                new_enable_efx = 1
            else:
                new_enable_efx = 0
            config.setValue('Sound/EnableEFX', new_enable_efx)

            new_sample_rate = self._tabs['fso_audio'].sampleRate.value()
            config.setValue('Sound/SampleRate', new_sample_rate)

            # joystick
            if self._tabs['fso_input'].controller.currentText() == self.tr('No Joystick'):
                new_joystick_id = 99999
            else:
                new_joystick_id = self._tabs['fso_input'].controller.currentIndex() - 1
            config.setValue(section + 'CurrentJoystick', new_joystick_id)

            # keyboard
            if sys.platform.startswith('linux'):
                key_layout = self._tabs['fso_input'].keyLayout.currentIndex()
                if key_layout == 0:
                    key_layout = 'default'
                else:
                    key_layout = self._tabs['fso_input'].keyLayout.itemText(key_layout)

                center.settings['keyboard_layout'] = key_layout
                center.settings['keyboard_setxkbmap'] = self._tabs['fso_input'].useSetxkbmap.isChecked()

            # networking
            net_types = {0: 'none', 1: 'dialup', 2: 'LAN'}
            new_net_connection = net_types[self._tabs['fso_network'].connectionType.currentIndex()]
            config.setValue(section + 'NetworkConnection', new_net_connection)

            net_speeds = {0: 'none', 1: 'Slow', 2: '56K', 3: 'ISDN', 4: 'Cable', 5: 'Fast'}
            new_net_speed = net_speeds[self._tabs['fso_network'].connectionSpeed.currentIndex()]
            config.setValue(section + 'ConnectionSpeed', new_net_speed)

            new_net_ip = self._tabs['fso_network'].forceAddress.text()
            if new_net_ip == '...':
                new_net_ip = ''

            if new_net_ip == '':
                config.remove('Network/CustomIP')
            else:
                config.setValue('Network/CustomIP', new_net_ip)

            new_net_port = self._tabs['fso_network'].localPort.text()
            if new_net_port == '0':
                new_net_port = ''
            elif new_net_port != '':
                try:
                    new_net_port = int(new_net_port)
                except ValueError:
                    new_net_port = ''

            if new_net_port == '':
                config.remove(section + 'ForcePort')
            else:
                config.setValue(section + 'ForcePort', new_net_port)

            # Save the new configuration.
            config.sync()
            self._tabs['fso_flags'].save()
        except:
            logging.exception('Failed to save the configuration!')
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to save the configuration!'))

        tab = self._tabs['lib_paths']
        sdl_path = tab.sdlPath.text()
        if sdl_path == 'auto':
            center.settings['sdl2_path'] = None
        else:
            center.settings['sdl2_path'] = sdl_path

        openal_path = tab.openAlPath.text()
        if openal_path == 'auto':
            center.settings['openal_path'] = None
        else:
            center.settings['openal_path'] = openal_path

        api.save_settings()

    def save_build(self):
        fs2_bin = self._builds[self._tabs['fso_settings'].build.currentIndex()][1]
        if not os.path.isfile(os.path.join(center.settings['fs2_path'], fs2_bin)):
            return

        old_bin = center.settings['fs2_bin']
        center.settings['fs2_bin'] = fs2_bin

        if not api.get_fso_flags():
            # We failed to run FSO but why?
            rc = runner.run_fs2_silent(['-help'])
            if rc == -128:
                msg = self.tr('The FSO binary "%s" is missing!') % fs2_bin
            elif rc == -127:
                # TODO: At this point we have run ldd twice already and the next call will run it again.
                # Is there any way to avoid this?
                _, missing = runner.fix_missing_libs(os.path.join(center.settings['fs2_path'], fs2_bin))
                msg = self.tr('The FSO binary "%s" is missing %s!') % (fs2_bin, util.human_list(missing))
            else:
                msg = self.tr('The FSO binary quit with code %d!') % rc

            center.settings['fs2_bin'] = old_bin
            QtWidgets.QMessageBox.critical(None, 'Knossos', msg)
            self.read_config()
        else:
            api.save_settings()
            center.signals.fs2_bin_changed.emit()

    def save_fred_build(self):
        fred_bin = self._fred_builds[self._tabs['fso_settings'].fredBuild.currentIndex()][1]
        if not os.path.isfile(os.path.join(center.settings['fs2_path'], fred_bin)):
            return

        center.settings['fred_bin'] = fred_bin
        api.save_settings()

    def save_language(self, p=None):
        tab = self._tabs['kn_settings']
        center.settings['language'] = str(tab.langSelect.currentData())
        api.save_settings()

        QtWidgets.QMessageBox.information(None, 'Knossos', 'Please restart Knossos to complete the language change.')

    def save_update_settings(self, p=None):
        tab = self._tabs['kn_settings']
        center.settings['update_channel'] = tab.updateChannel.currentText()
        center.settings['update_notify'] = tab.updateNotify.checkState() == QtCore.Qt.Checked
        api.save_settings()

    def save_report_settings(self, p=None):
        tab = self._tabs['kn_settings']
        center.settings['use_raven'] = tab.reportErrors.checkState() == QtCore.Qt.Checked

        if center.settings['use_raven']:
            api.enable_raven()
        else:
            api.disable_raven()

        api.save_settings()

    def show_fso_log(self):
        logpath = os.path.join(api.get_fso_profile_path(), 'data/fs2_open.log')

        if not os.path.isfile(logpath):
            QtWidgets.QMessageBox.warning(None, 'Knossos',
                self.tr('Sorry, but I can\'t find the fs2_open.log file.\nDid you run the debug build?'))
        else:
            LogViewer(logpath)

    def show_fso_cfg_folder(self):
        path = api.get_fso_profile_path()
        QtGui.QDesktopServices.openUrl(QtCore.QUrl('file://' + path))

    def show_knossos_log(self):
        LogViewer(launcher.log_path)

    def clear_hash_cache(self):
        util.HASH_CACHE = dict()
        run_task(CheckTask())
        QtWidgets.QMessageBox.information(None, 'Knossos', self.tr('Done!'))

