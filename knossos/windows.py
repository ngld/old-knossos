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

import os
import sys
import logging
import shlex
import functools
import json
import semantic_version

from . import uhf
uhf(__name__)

from . import center, util, integration, api, web, repo
from .qt import QtCore, QtGui, QtWidgets, load_styles
from .ui.hell import Ui_MainWindow as Ui_Hell
from .ui.gogextract import Ui_GogExtractDialog
from .ui.flags import Ui_FlagsDialog
from .ui.install import Ui_InstallDialog
from .ui.mod_settings import Ui_ModSettingsDialog
from .ui.mod_versions import Ui_ModVersionsDialog
from .ui.log_viewer import Ui_LogDialog
from .tasks import run_task, GOGExtractTask, InstallTask, UninstallTask, WindowsUpdateTask, CheckFilesTask

# Keep references to all open windows to prevent the GC from deleting them.
_open_wins = []
translate = QtCore.QCoreApplication.translate


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

    def tr(self, *args):
        return translate(self.__class__.__name__, *args)


class HellWindow(Window):
    _tasks = None
    _mod_filter = 'home'
    _search_text = ''
    _updating_mods = None
    browser_ctrl = None
    progress_win = None

    def __init__(self, window=True):
        super(HellWindow, self).__init__(window)
        self._tasks = {}
        self._updating_mods = {}

        self._create_win(Ui_Hell, QMainWindow)
        self.browser_ctrl = web.BrowserCtrl(self.win.webView)
        self.win.verticalLayout.setContentsMargins(0, 0, 0, 0)

        self.win.webView.loadStarted.connect(self.show_indicator)
        self.win.webView.loadFinished.connect(self.check_loaded)

        center.signals.update_avail.connect(self.ask_update)
        center.signals.task_launched.connect(self.watch_task)
        center.signals.repo_updated.connect(self.update_mod_list)

        self.win.setWindowTitle(self.win.windowTitle() + ' ' + center.VERSION)
        self.win.progressInfo.hide()
        self.open()

    def _del(self):
        center.signals.update_avail.disconnect(self.ask_update)
        center.signals.task_launched.disconnect(self.watch_task)

        # Trying to free this object usually leads to memory corruption
        # See http://pyqt.sourceforge.net/Docs/PyQt5/gotchas.html#crashes-on-exit
        # Since this is the main window and should only be closed whenever the application exits, skipping this
        # won't lead to memory leaks.
        # super(HellWindow, self)._del()

    def finish_init(self):
        self.check_fso()
        api.init_self()

    def check_fso(self):
        if 'KN_WELCOME' not in os.environ and center.settings['base_path'] is not None:
            self.update_mod_buttons('home')
        else:
            self.browser_ctrl.bridge.showWelcome.emit()

    def ask_update(self, version):
        # We only have an updater for windows.
        if sys.platform.startswith('win'):
            msg = self.tr('There\'s an update available!\nDo you want to install Knossos %s now?') % str(version)
            buttons = QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            result = QtWidgets.QMessageBox.question(center.app.activeWindow(), 'Knossos', msg, buttons)
            if result == QtWidgets.QMessageBox.Yes:
                run_task(WindowsUpdateTask())
        else:
            msg = self.tr('There\'s an update available!\nYou should update to Knossos %s.') % str(version)
            QtWidgets.QMessageBox.information(center.app.activeWindow(), 'Knossos', msg)

    def update_repo_list(self):
        api.fetch_list()

    def search_mods(self):
        mods = None

        if self._mod_filter in ('home', 'develop'):
            mods = center.installed.mods
        elif self._mod_filter == 'explore':
            mods = {}
            for mid, mvs in center.mods.mods.items():
                if mid not in center.installed.mods:
                    mods[mid] = mvs
        # elif self._mod_filter == 'updates':
        #     mods = {}
        #     for mid in center.installed.get_updates():
        #         mods[mid] = center.installed.mods[mid]
        else:
            mods = {}

        # Now filter the mods.
        query = self._search_text
        result = []
        for mid, mvs in mods.items():
            if query in mvs[0].title.lower():
                mod = mvs[0]
                item = mod.get()
                item['progress'] = 0
                item['progress_info'] = {}

                try:
                    rmod = center.mods.query(mod)
                except repo.ModNotFound:
                    rmod = None

                if rmod and rmod.version > mod.version:
                    item['status'] = 'update'
                elif mod.mid in self._updating_mods:
                    item['status'] = 'updating'
                    item['progress'] = self._updating_mods[mod.mid]
                else:
                    item['status'] = 'ready'

                    if self._mod_filter == 'home':
                        for pkg in mod.packages:
                            if pkg.files_checked > 0 and pkg.files_ok < pkg.files_checked:
                                item['status'] = 'error'
                                break

                result.append(item)

        result.sort(key=lambda m: m['title'])
        return result, self._mod_filter

    def update_mod_list(self):
        result, filter_ = self.search_mods()

        if filter_ in ('home', 'explore', 'develop'):
            self.browser_ctrl.bridge.updateModlist.emit(result, filter_)

    def show_settings(self):
        pass

    def show_indicator(self):
        self.win.setCursor(QtCore.Qt.BusyCursor)

    def check_loaded(self, success):
        self.win.unsetCursor()

    def update_mod_buttons(self, clicked=None):
        if center.settings['base_path'] is not None:
            self._mod_filter = clicked
            self.update_mod_list()

    def perform_search(self, term):
        self._search_text = term.lower()
        self.update_mod_list()

    def watch_task(self, task):
        logging.debug('Task "%s" (%d, %s) started.', task.title, id(task), task.__class__)
        self._tasks[id(task)] = task
        self.browser_ctrl.bridge.taskStarted.emit(id(task), task.title, [m.mid for m in task.mods])

        for m in task.mods:
            self._updating_mods[m.mid] = 0

        task.done.connect(functools.partial(self._forget_task, task))
        task.progress.connect(functools.partial(self._track_progress, task))

        if len(task.mods) == 0:
            if len(self._tasks) == 1:
                self.win.progressInfo.show()
                self.win.progressLabel.setText(task.title)
                self.win.progressBar.setValue(0)

                integration.current.show_progress(0)
            else:
                # TODO: Stop being lazy and calculate the aggregate progress.
                self.win.progressBar.hide()
                self.win.progressLabel.setText(self.tr('Working...'))

    def _track_progress(self, task, pi):
        self.browser_ctrl.bridge.taskProgress.emit(id(task), pi[0] * 100, json.dumps(pi[1]))

        for m in task.mods:
            self._updating_mods[m.mid] = pi[0] * 100

        if len(self._tasks) == 1:
            integration.current.set_progress(pi[0])
            self.win.progressBar.setValue(pi[0] * 100)

    def _forget_task(self, task):
        logging.debug('Task "%s" (%d) finished.', task.title, id(task))
        self.browser_ctrl.bridge.taskFinished.emit(id(task))
        del self._tasks[id(task)]

        for m in task.mods:
            if m.mid in self._updating_mods:
                del self._updating_mods[m.mid]

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


class GogExtractWindow(Window):

    def __init__(self, window=True):
        super(GogExtractWindow, self).__init__(window)

        self._create_win(Ui_GogExtractDialog)

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
        path = QtWidgets.QFileDialog.getOpenFileName(self.win,
            self.tr('Please select the setup_freespace2_*.exe file.'),
            os.path.expanduser('~/Downloads'), self.tr('Executable (*.exe)'))

        if isinstance(path, tuple):
            path = path[0]

        if path is not None and path != '':
            if not os.path.isfile(path):
                QtWidgets.QMessageBox.critical(self.win, self.tr('Not a file'), self.tr('Please select a proper file!'))
                return

            self.win.gogPath.setText(os.path.abspath(path))

    def select_dest(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self.win, self.tr('Please select the destination directory.'),
            os.path.expanduser('~/Documents'))

        if path is not None and path != '':
            if not os.path.isdir(path):
                QtWidgets.QMessageBox.critical(self.win, self.tr('Not a directory'),
                    self.tr('Please select a proper directory!'))
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

        self._create_win(Ui_FlagsDialog)
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
            self.win.cmdLine.setPlainText(self.tr('Until you select a working FS2 build, I won\'t be able to help you.'))
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
        if self.mod:
            fs2_bin = self.mod.get_bin()
        else:
            fs2_bin = center.settings['fs2_bin']

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
        self._create_win(Ui_InstallDialog)
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
            msg = self.tr('I\'m sorry but you won\'t be able to install "%s" because "%s" is missing!') % (
                self._mod.title, exc.mid)
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
                    sub.setText(1, self.tr('Installed'))

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
        center.main_win.update_mod_buttons('home')

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
        self._create_win(Ui_ModSettingsDialog, QDialog)
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
                            p_check.setText(pkg.name + self.tr(' (missing)'))
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
                    item[0].setText(item[2].name + self.tr(' (missing)'))

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
                    QtWidgets.QMessageBox.critical(None, 'Knossos',
                        self.tr("I'm sorry but I can't install the selected packages because the dependency " +
                            '"%s" is missing!') % exc.mid)
                else:
                    QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr("I'm sorry but I can't install new " +
                        "packages for this mod since it's not available anymore!"))

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
            msg += self.tr("I'm going to remove %s.\n") % util.human_list([p.name for p in remove])

        if len(install) > 0:
            msg += self.tr("I'm going to install %s.\n") % util.human_list(
                [p.name for p in install if not center.installed.is_installed(p)])

        box = QtWidgets.QMessageBox()
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setText(msg)
        box.setInformativeText(self.tr('Continue?'))
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
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr('This mod is missing the dependency "%s"!') % exc.mid)
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
            sel.addItem(self.tr('Latest (%s)') % versions[0].version, None)

            pin = center.installed.get_pin(mod)
            for n, mv in enumerate(versions):
                sel.addItem(str(mv.version), mv.version)

                if pin == mv.version:
                    sel.setCurrentIndex(n + 1)

            editBut = QtWidgets.QPushButton(self.tr('Edit'))

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
                    report += '<h2>%s</h2>' % (self.tr('Loose files (%d)') % (len(info['loose'])))
                    report += '<ul><li>' + '</li><li>'.join(sorted(info['loose'])) + '</li></ul>'
            else:
                report += self.tr('<h2>%s (%d/%d files OK)</h2>') % (pkg.name, s, c)
                ok_count = len(info['ok'])
                corr_count = len(info['corrupt'])
                miss_count = len(info['missing'])

                report += '<ul>'

                if ok_count > 0:
                    if corr_count > 0 or miss_count > 0:
                        report += '<ul><li>%s<ul>' % self.tr('OK')
                        report += '<li>' + '</li><li>'.join(sorted(info['ok'])) + '</li>'
                        report += '</ul></li>'
                    else:
                        report += '<li>' + '</li><li>'.join(sorted(info['ok'])) + '</li>'

                if corr_count > 0:
                    report += '<li>%s<ul>' % self.tr('Corrupted')
                    report += '<li>' + '</li><li>'.join(sorted(info['corrupt'])) + '</li>'
                    report += '</ul></li>'

                if miss_count > 0:
                    report += '<li>%s<ul>' % self.tr('Missing')
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
        modpath = self._mod.folder

        for pkg, s, c, info in task.get_results():
            if pkg is None:
                for name in info['loose']:
                    item = os.path.join(modpath, name)
                    logging.info('Deleteing "%s"...', item)
                    os.unlink(item)

        self.win.unsetCursor()
        QtWidgets.QMessageBox.information(None, 'Knossos', self.tr('Done!'))

    def repair_files(self):
        try:
            run_task(InstallTask(self._mod.packages))
        except repo.ModNotFound as exc:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr("I can't repair this mod: %s") % str(exc))


class ModVersionsWindow(Window):
    _mod = None
    _versions = None

    def __init__(self, mod, window=True):
        super(ModVersionsWindow, self).__init__(window)

        self._mod = mod
        self._versions = []
        self._create_win(Ui_ModVersionsDialog, QDialog)
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
                logging.warning('Version "%s" for mod "%s" (%s) is empty! (It has no packages!!)',
                    m.version, m.title, m.mid)
                continue

            label = str(m.version)
            if m.version in local_versions:
                label += self.tr(' (l)', 'This marks a version as *l*ocal-only. See also next line.')

            item = QtWidgets.QListWidgetItem(label, self.win.versionList)
            item.setData(QtCore.Qt.UserRole + 1, m)

            if m.version in local_versions:
                item.setToolTip(self.tr('This version is installed locally but not available anymore!'))

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
        self._create_win(Ui_ModSettingsDialog, QDialog)

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

        self._create_win(Ui_LogDialog)
        self.win.pathLabel.setText(path)

        if not os.path.isfile(path):
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                self.tr('Log file %s can\'t be shown because it\'s missing!') % path)
            return

        with open(path, 'r') as stream:
            self.win.content.setPlainText(stream.read())

        self.open()
