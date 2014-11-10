#!/usr/bin/python
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

from . import uhf
uhf(__name__)

from . import center, util, clibs, progress, repo, integration, api, web
from .qt import QtCore, QtGui
from .ui.main import Ui_MainWindow
from .ui.nebula import Ui_MainWindow as Ui_Nebula
from .ui.modinfo import Ui_Dialog as Ui_Modinfo
from .ui.add_repo import Ui_Dialog as Ui_AddRepo
from .ui.settings2 import Ui_Dialog as Ui_Settings
from .tasks import run_task, CheckTask, InstallTask, UninstallTask, WindowsUpdateTask
from .windows import Window, QMainWindow, FlagsWindow, GogExtractWindow


class MainWindow(Window):
    progress_win = None
    settings_tab = None
    browser_ctrl = None
    dep_processing = False

    def __init__(self, parent=None):
        super(MainWindow, self).__init__()

        if parent is None:
            self.win = util.init_ui(Ui_MainWindow(), QMainWindow())
        else:
            self.win = util.init_ui(Ui_MainWindow(), QMainWindow(parent.win, QtCore.Qt.Dialog))
            self.win.setWindowModality(QtCore.Qt.WindowModal)

        self.progress_win = progress.ProgressDisplay()

        if hasattr(sys, 'frozen'):
            # Add note about bundled content.
            # NOTE: This will appear even when this script is bundled with py2exe or a similiar program.
            self.win.aboutLabel.setText(self.win.aboutLabel.text().replace('</body>', '<p>' +
                                        'This bundle was created with <a href="http://pyinstaller.org">PyInstaller</a>' +
                                        ' and contains a 7z executable as well as SDL and OpenAL libraries.</p></body>'))
        
        if sys.platform.startswith('win') or sys.platform.startswith('linux'):
            self.win.schemeHandler.clicked.connect(api.install_scheme_handler)
        else:
            self.win.schemeHandler.hide()
        
        # Prepare the status bar

        label = QtGui.QLabel(self.win.statusbar)
        label.setText('Version: ' + center.VERSION)
        self.win.statusbar.addWidget(label)

        self.progress_win.set_statusbar(self.win.statusbar)
        
        center.signals.repo_updated.connect(self.update_list)
        
        center.signals.update_avail.connect(self.ask_update)
        self.win.updateButton.hide()
        self.win.updateButton.clicked.connect(self.run_update)

        self.update_repo_list()
        
        self.win.aboutLabel.linkActivated.connect(QtGui.QDesktopServices.openUrl)
        self.win.gogextractButton.clicked.connect(self.do_gog_extract)

        self.win.apply_sel.clicked.connect(self.apply_selection)
        self.win.reset_sel.clicked.connect(self.reset_selection)
        self.win.update.clicked.connect(api.fetch_list)
        
        self.win.modTree.itemActivated.connect(self.select_mod)
        self.win.modTree.itemChanged.connect(self.autoselect_deps)
        self.win.modTree.sortItems(0, QtCore.Qt.AscendingOrder)
        self.win.modTree.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        
        self.win.addSource.clicked.connect(self.add_repo)
        self.win.editSource.clicked.connect(self.edit_repo)
        self.win.removeSource.clicked.connect(self.remove_repo)
        self.win.sourceList.itemDoubleClicked.connect(self.edit_repo)
        
        self.win.enforceDeps.setCheckState(QtCore.Qt.Checked if center.settings['enforce_deps'] else QtCore.Qt.Unchecked)
        self.win.enforceDeps.stateChanged.connect(self.update_enforce_deps)
        self.win.versionLabel.setText(center.VERSION)
        self.win.maxDownloads.setText(str(center.settings['max_downloads']))
        self.win.maxDownloads.textEdited.connect(self.update_max_downloads)
        self.win.uiMode.setCurrentIndex(0 if center.settings['ui_mode'] == 'traditional' else 1)
        self.win.uiMode.currentIndexChanged.connect(self.update_ui_mode)
        
        self.browser_ctrl = web.BrowserCtrl(self.win.webView)
        
        # NOTE: Assign the model to a variable to prevent a segfault with PySide. (WTF?!)
        m = self.win.sourceList.model()
        m.rowsMoved.connect(self.reorder_repos)
        del m

        # TODO: I should probably get rid of the SettingsWindow() and properly embed this.
        self.settings_tab = SettingsTab(self.win.fsoSettings)

        # Fix a weird display bug
        self.win.tabs.setCurrentIndex(2)
        self.win.tabs.setCurrentIndex(1)
        self.win.webView.setMaximumSize(999999, 999999)

        self.check_fso()
        #self.win.move(manager.app.desktop().screen().rect().center() - self.win.rect().center())

    def _del(self):
        self.settings_tab._del2()
        super(MainWindow, self)._del()

    def check_fso(self):
        if center.settings['fs2_path'] is None:
            self.win.tabs.setTabEnabled(0, False)
            self.win.tabs.setTabEnabled(2, False)
        else:
            self.win.tabs.setTabEnabled(0, True)
            self.win.tabs.setTabEnabled(2, True)
            self.settings_tab.read_config()

            QtCore.QTimer.singleShot(1, self.update_list)

    def do_gog_extract(self):
        GogExtractWindow(self)

    # The mod tree tab
    
    def build_mod_tree(self, mod=None, parent_el=None):
        if mod is None:
            mods = center.settings['mods'].get_tree()
        else:
            mods = mod.get_submods()

        rows = dict()

        for mod in mods:
            row = QtGui.QTreeWidgetItem((mod.title, str(mod.version), ''))
            row.setData(0, QtCore.Qt.UserRole + 2, mod)
            row.setData(0, QtCore.Qt.UserRole + 3, False)

            rows[mod.mid] = row

            if parent_el is None:
                self.win.modTree.addTopLevelItem(row)
            else:
                parent_el.addChild(row)

            rows.update(self.build_mod_tree(mod, row))

        return rows

    def read_tree(self, parent, items=None):
        if items is None:
            items = []
        
        if isinstance(parent, QtGui.QTreeWidget):
            for i in range(0, parent.topLevelItemCount()):
                item = parent.topLevelItem(i)
                items.append((item, None))
                
                self.read_tree(item, items)
        else:
            for i in range(0, parent.childCount()):
                item = parent.child(i)
                items.append((item, parent))
                
                self.read_tree(item, items)
        
        return items

    def update_list(self):
        if center.settings['mods'] is None:
            api.fetch_list()
            return

        # Make sure the mod tree is empty.
        self.dep_processing = True
        self.win.modTree.clear()
        rows = self.build_mod_tree()
        updates = center.installed.get_updates()
        
        for mid, mvs in center.settings['mods'].mods.items():
            mod = mvs[0]
            titem = rows[mod.mid]
            rc = 0
            ri = 0

            for pkg in mod.packages:
                try:
                    pinfo = center.installed.query(pkg)
                except repo.ModNotFound:
                    pinfo = None

                if pinfo is None:
                    cstate = QtCore.Qt.Unchecked
                    status = 'Not installed'
                elif mod.version in updates.get(mod.mid, {}):
                    cstate = QtCore.Qt.PartiallyChecked
                    status = 'Update available'
                elif pinfo.files_ok < pinfo.files_checked:
                    cstate = QtCore.Qt.PartiallyChecked
                    status = '%d corrupted files' % (pinfo.files_checked - pinfo.files_ok)
                else:
                    cstate = QtCore.Qt.Checked
                    status = 'Installed'
                
                row = QtGui.QTreeWidgetItem((pkg.name, str(mod.version), status))
                row.setCheckState(0, cstate)
                row.setData(0, QtCore.Qt.UserRole, cstate)
                row.setData(0, QtCore.Qt.UserRole + 2, pkg)
                row.setData(0, QtCore.Qt.UserRole + 3, False)
                
                if pkg.status == 'required':
                    row.setDisabled(True)
                    rc += 1

                    if pinfo is not None:
                        ri += 1

                titem.addChild(row)

            if len(mvs) > 1:
                v_item = QtGui.QTreeWidgetItem(('Other Versions', '', ''))
                v_item.setData(0, QtCore.Qt.UserRole + 2, None)
                v_item.setData(0, QtCore.Qt.UserRole + 3, False)
                titem.addChild(v_item)

                for mod in mvs[1:]:
                    m_item = QtGui.QTreeWidgetItem((str(mod.version), str(mod.version), ''))
                    m_item.setData(0, QtCore.Qt.UserRole + 2, mod)
                    m_item.setData(0, QtCore.Qt.UserRole + 3, False)
                    v_item.addChild(m_item)

                    if center.installed.is_installed(mod):
                        m_item.setCheckState(0, QtCore.Qt.Checked)
                    else:
                        m_item.setCheckState(0, QtCore.Qt.Unchecked)

                    for pkg in mod.packages:
                        try:
                            pinfo = center.installed.query(pkg)
                        except repo.ModNotFound:
                            pinfo = None

                        if pinfo is None:
                            cstate = QtCore.Qt.Unchecked
                            status = 'Not installed'
                        elif mod.version in updates.get(mod.mid, {}):
                            cstate = QtCore.Qt.PartiallyChecked
                            status = 'Update available'
                        elif pinfo.files_ok < pinfo.files_checked:
                            cstate = QtCore.Qt.PartiallyChecked
                            status = '%d corrupted files' % (pinfo.files_checked - pinfo.files_ok)
                        else:
                            cstate = QtCore.Qt.Checked
                            status = 'Installed'

                        row = QtGui.QTreeWidgetItem((pkg.name, str(mod.version), status))
                        row.setCheckState(0, cstate)
                        row.setData(0, QtCore.Qt.UserRole, cstate)
                        row.setData(0, QtCore.Qt.UserRole + 2, pkg)
                        row.setData(0, QtCore.Qt.UserRole + 3, False)

                        if pkg.status == 'required':
                            row.setDisabled(True)
                        
                        m_item.addChild(row)

            if ri == 0:
                state = QtCore.Qt.Unchecked
            elif ri == rc:
                state = QtCore.Qt.Checked
            else:
                state = QtCore.Qt.PartiallyChecked

            titem.setCheckState(0, state)
            titem.setData(0, QtCore.Qt.UserRole, state)

        self.dep_processing = False
        integration.current.annoy_user()

    def check_list(self):
        self.win.modTree.clear()
        
        if center.settings['fs2_path'] is None:
            return
        
        if center.settings['mods'] is None:
            api.fetch_list()
        else:
            return run_task(CheckTask(center.settings['mods'].get_list()))

    def autoselect_deps(self, item, col):
        if self.dep_processing:
            return

        self.dep_processing = True
        
        item.setData(0, QtCore.Qt.UserRole + 3, False)
        info = item.data(0, QtCore.Qt.UserRole + 2)
        if isinstance(info, repo.Mod):
            was_installed = item.data(0, QtCore.Qt.UserRole) in (QtCore.Qt.Checked, QtCore.Qt.PartiallyChecked)

            if item.checkState(0) == QtCore.Qt.Checked:
                # Check all required and recommended packages
                for i in range(0, item.childCount()):
                    child = item.child(i)
                    pkg = child.data(0, QtCore.Qt.UserRole + 2)

                    if isinstance(pkg, repo.Package):
                        state = QtCore.Qt.Checked
                        if pkg.status != 'required':
                            if was_installed:
                                state = child.data(0, QtCore.Qt.UserRole)
                            elif pkg.status == 'optional':
                                state = QtCore.Qt.Unchecked

                        child.setCheckState(0, QtCore.Qt.CheckState(state))

            elif item.checkState(0) == QtCore.Qt.Unchecked:
                # Uncheck all packages
                for i in range(0, item.childCount()):
                    child = item.child(i)
                    pkg = child.data(0, QtCore.Qt.UserRole + 2)

                    if isinstance(pkg, repo.Package):
                        child.setCheckState(0, QtCore.Qt.Unchecked)

        # Cascade dependencies
        tree = self.read_tree(self.win.modTree)
        selection = []
        for item, _ in tree:
            if item.data(0, QtCore.Qt.UserRole + 3):
                item.setCheckState(0, QtCore.Qt.Unchecked)
            else:
                pkg = item.data(0, QtCore.Qt.UserRole + 2)
                if isinstance(pkg, repo.Package) and item.checkState(0) != QtCore.Qt.Unchecked:
                    selection.append(pkg)

        try:
            selection = []  # center.settings['mods'].process_pkg_selection(selection)
        except:
            logging.exception('Failed to satisfy dependencies!')
            self.reset_selection()
            # TODO: Message to the user?
            self.dep_processing = False
            return

        for item, _ in tree:
            pkg = item.data(0, QtCore.Qt.UserRole + 2)
            if isinstance(pkg, repo.Package) and pkg in selection:
                if item.checkState(0) != QtCore.Qt.Checked:
                    if item.checkState(0) == QtCore.Qt.Unchecked:
                        item.setData(0, QtCore.Qt.UserRole + 3, True)

                    item.setCheckState(0, QtCore.Qt.Checked)

        self.dep_processing = False

    def apply_selection(self):
        if center.settings['mods'] is None:
            return
        
        install = []
        uninstall = []
        items = self.read_tree(self.win.modTree)
        for item, parent in items:
            pkg = item.data(0, QtCore.Qt.UserRole + 2)
            if not isinstance(pkg, repo.Package):
                continue

            if item.checkState(0) == item.data(0, QtCore.Qt.UserRole):
                # Unchanged
                continue
            
            if item.checkState(0):
                # Install
                install.append(pkg)
            else:
                # Uninstall
                uninstall.append(pkg)

        try:
            install = center.settings['mods'].process_pkg_selection(install)
        except:
            logging.exception('Failed to process package selection!')
            msg = 'There probably was some kind of dependency conflict.\nI\'m sorry but I can\'t install the packages you selected.'
            QtGui.QMessageBox.critical(self.win, 'Error', msg)
            return
        
        if len(install) == 0 and len(uninstall) == 0:
            QtGui.QMessageBox.warning(self.win, 'Warning', 'You didn\'t change anything! There\'s nothing for me to do...')
            return
        
        if len(install) > 0:
            install_titles = set()
            for pkg in install:
                install_titles.add(pkg.get_mod().title)

            msg = QtGui.QMessageBox()
            msg.setIcon(QtGui.QMessageBox.Question)
            msg.setText('Do you really want to install these mods?')
            msg.setInformativeText(', '.join(install_titles) + ' will be installed.')
            msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            msg.setDefaultButton(QtGui.QMessageBox.Yes)
            
            if msg.exec_() == QtGui.QMessageBox.Yes:
                run_task(InstallTask(install))
        
        if len(uninstall) > 0:
            uninstall_titles = set()
            for pkg in uninstall:
                uninstall_titles.add(pkg.get_mod().title)

            msg = QtGui.QMessageBox()
            msg.setIcon(QtGui.QMessageBox.Question)
            msg.setText('Do you really want to remove these mods?')
            msg.setInformativeText(', '.join(uninstall_titles) + ' will be removed.')
            msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            msg.setDefaultButton(QtGui.QMessageBox.Yes)
            
            if msg.exec_() == QtGui.QMessageBox.Yes:
                run_task(UninstallTask(uninstall))

    def reset_selection(self):
        items = self.read_tree(self.win.modTree)
        for row, parent in items:
            value = row.data(0, QtCore.Qt.UserRole)
            if value is not None:
                row.setCheckState(0, QtCore.Qt.CheckState(value))

    def select_mod(self, item, col):
        mod = item.data(0, QtCore.Qt.UserRole + 2)
        if not isinstance(mod, repo.Mod):
            if isinstance(mod, repo.Package):
                # This is a package...
                self.select_pkg(item, col)
            return

        ModInfoWindow(self, mod)

    def select_pkg(self, item, col):
        pkg = item.data(0, QtCore.Qt.UserRole + 2)
        
        if not isinstance(pkg, repo.Package):
            if isinstance(pkg, repo.Mod):
                self.select_mod(item, col)
            return

        PkgInfoWindow(self, pkg)

    # Settings tab
    def update_repo_list(self):
        self.win.sourceList.clear()
        
        for i, r in enumerate(center.settings['repos']):
            item = QtGui.QListWidgetItem(r[1], self.win.sourceList)
            item.setData(QtCore.Qt.UserRole, i)

    def _edit_repo(self, repo=None, idx=None):
        win = util.init_ui(Ui_AddRepo(), util.QDialog(self.win))
        
        win.okButton.clicked.connect(win.accept)
        win.cancelButton.clicked.connect(win.reject)
        
        if repo is not None:
            win.source.setText(repo[0])
            win.title.setText(repo[1])
        
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
        item = self.win.sourceList.currentItem()
        if item is not None:
            idx = item.data(QtCore.Qt.UserRole)
            self._edit_repo(center.settings['repos'][idx], idx)

    def remove_repo(self):
        item = self.win.sourceList.currentItem()
        if item is not None:
            idx = item.data(QtCore.Qt.UserRole)
            answer = QtGui.QMessageBox.question(self.win, 'Are you sure?', 'Do you really want to remove "%s"?' % (item.text()),
                                                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            
            if answer == QtGui.QMessageBox.Yes:
                del center.settings['repos'][idx]
                
                api.save_settings()
                self.update_repo_list()

    def reorder_repos(self, parent, s_start, s_end, d_parent, d_row):
        repos = []
        for row in range(0, self.win.sourceList.count()):
            item = self.win.sourceList.item(row)
            repos.append(center.settings['repos'][item.data(QtCore.Qt.UserRole)])
        
        center.settings['repos'] = repos
        api.save_settings()
        
        # NOTE: This call is normally redundant but I want to make sure that
        # the displayed list is always the same as the actual list in settings['repos'].
        # Once this feature is stable this call can be removed.
        self.update_repo_list()

    def update_enforce_deps(self):
        center.settings['enforce_deps'] = self.win.enforceDeps.checkState() == QtCore.Qt.Checked
        api.save_settings()

    def update_max_downloads(self):
        old_num = num = center.settings['max_downloads']

        try:
            center.settings['max_downloads'] = num = int(self.win.maxDownloads.text())
        except:
            pass

        self.win.maxDownloads.setText(str(num))

        if num != old_num:
            util.DL_POOL.set_capacity(num)
            api.save_settings()

    def update_ui_mode(self, idx):
        if idx == 0:
            center.settings['ui_mode'] = 'traditional'
        elif idx == 1:
            center.settings['ui_mode'] = 'nebula'
        else:
            center.settings['ui_mode'] = 'hell'

        api.save_settings()
        api.switch_ui_mode(center.settings['ui_mode'])

    def ask_update(self, version):
        # We only have an updater for windows.
        if sys.platform.startswith('win'):
            self.win.updateButton.show()

            msg = 'There\'s an update available!\nDo you want to install Knossos %s now?' % str(version)
            buttons = QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
            result = QtGui.QMessageBox.question(center.app.activeWindow(), 'Knossos', msg, buttons)
            if result == QtGui.QMessageBox.Yes:
                self.run_update()
        else:
            msg = 'There\'s an update available!\nYou should update to Knossos %s.' % str(version)
            QtGui.QMessageBox.information(center.app.activeWindow(), 'Knossos', msg)

    def run_update(self):
        run_task(WindowsUpdateTask())


class NebulaWindow(Window):
    browser_ctrl = None
    support_win = None
    progress_win = None

    def __init__(self):
        super(NebulaWindow, self).__init__()

        self.support_win = MainWindow(self)
        self.progress_win = self.support_win.progress_win
        self.win = util.init_ui(Ui_Nebula(), QMainWindow())

        label = QtGui.QLabel(self.win.statusbar)
        label.setText('Version: ' + center.VERSION)
        self.win.statusbar.addWidget(label)
        self.progress_win.set_statusbar(self.win.statusbar)

        self.win.modlistButton.clicked.connect(self.show_mod_list)
        self.win.nebulaButton.clicked.connect(self.show_nebula)
        self.win.fsoSettingsButton.clicked.connect(self.show_fso_settings)
        self.win.settingsButton.clicked.connect(self.show_settings)
        self.win.modtreeButton.clicked.connect(self.show_mod_tree)
        self.win.aboutButton.clicked.connect(self.show_about)

        self.browser_ctrl = web.BrowserCtrl(self.win.webView)
        self.show_mod_list()
        #self.win.move(manager.app.desktop().screen().rect().center() - self.win.rect().center())

    def _del(self):
        self.support_win.close()
        super(NebulaWindow, self)._del()

    def check_fso(self):
        self.support_win.check_fso()

    def update_repo_list(self):
        self.support_win.update_repo_list()

    def open_support(self):
        if self.support_win is None:
            self.support_win = MainWindow()
            self.support_win.open()
        elif self.support_win.closed:
            self.support_win.open()
        else:
            self.support_win.win.activateWindow()
            self.support_win.win.raise_()

    def show_mod_list(self):
        self.win.webView.load('qrc:///html/welcome.html')

    def show_nebula(self):
        self.win.webView.load(center.settings['nebula_link'])

    def show_fso_settings(self):
        self.open_support()
        self.support_win.win.tabs.setCurrentIndex(2)

    def show_settings(self):
        self.open_support()
        self.support_win.win.tabs.setCurrentIndex(3)

    def show_mod_tree(self):
        self.open_support()
        self.support_win.win.tabs.setCurrentIndex(0)

    def show_about(self):
        self.open_support()
        self.support_win.win.tabs.setCurrentIndex(4)


class ModInfoWindow(Window):
    _mod = None

    def __init__(self, main_win, mod):
        super(ModInfoWindow, self).__init__()

        self._mod = mod

        self.win = util.init_ui(Ui_Modinfo(), util.QDialog(main_win.win))
        self.win.setModal(True)

        self.win.modname.setText(mod.title + ' - ' + str(mod.version))
        
        if mod.logo is None:
            self.win.logo.hide()
        else:
            img = QtGui.QPixmap()
            img.load(mod.logo_path)
            self.win.logo.setPixmap(img)
        
        self.win.desc.setPlainText(mod.description)
        self.win.note.setPlainText(mod.notes)

        self.win.note.appendPlainText('\nContents:\n* ' + '\n* '.join([util.pjoin(mod.folder, item) for item in sorted([f['filename'] for f in mod.get_files()])]))
        try:
            inst_mod = center.installed.query(mod)
            self.win.note.appendPlainText('\n* '.join(inst_mod.check_notes))
        except repo.ModNotFound:
            pass

        self.win.closeButton.clicked.connect(self.win.close)
        self.win.settingsButton.clicked.connect(self.show_settings)
        self.win.runButton.clicked.connect(self.do_run)
        self.open()
        
        self.win.note.verticalScrollBar().setValue(0)

    def do_run(self):
        api.run_mod(self._mod)
    
    def show_settings(self):
        FlagsWindow(self.win, self._mod)


class PkgInfoWindow(Window):
    
    def __init__(self, main_win, pkg):
        super(PkgInfoWindow, self).__init__()

        self.win = util.init_ui(Ui_Modinfo(), util.QDialog(main_win.win))
        self.win.setModal(True)
        self.win.modname.setText(pkg.name)
        self.win.logo.hide()
        self.win.tabs.setTabEnabled(2, False)
        self.win.tabs.setCurrentIndex(1)

        self.win.desc.setPlainText(pkg.notes)

        try:
            pinfo = center.installed.query(pkg)
        except repo.ModNotFound:
            pinfo = None

        if pinfo is not None and len(pinfo.check_notes) > 0:
            self.win.note.appendPlainText('\nCheck messages:\n* ' + '\n* '.join(pinfo.check_notes))
        
        deps = pkg.resolve_deps()
        if len(deps) > 0:
            lines = []
            for dep in deps:
                line = '* ' + dep[0].name
                if center.installed.is_installed(dep[0]):
                    line += ' (installed)'
                
                lines.append(line)
            
            self.win.note.appendPlainText('\nDependencies:\n' + '\n'.join(lines))

        self.win.closeButton.clicked.connect(self.win.close)
        self.win.settingsButton.hide()
        self.win.runButton.hide()
        self.open()
        
        self.win.note.verticalScrollBar().setValue(0)


class SettingsWindow(Window):
    config = None
    mod = None
    _app = None
    
    def __init__(self, mod, app=None):
        self.mod = mod
        self.win = util.init_ui(Ui_Settings(), util.QDialog(center.main_win))
        self.win.setModal(True)

        self.win.browseButton.clicked.connect(api.select_fs2_path)
        
        if mod is None:
            self.win.cmdButton.setText('Default command line flags')
        else:
            self.win.cmdButton.setText('Command line flags for: {0}'.format(mod.title))
        
        self.win.cmdButton.clicked.connect(self.show_flagwin)
        self.read_config()
        
        self.win.build.activated.connect(self.save_build)
        self.win.runButton.clicked.connect(self.run_mod)
        self.win.saveButton.clicked.connect(self.write_config)
        self.win.cancelButton.clicked.connect(self.win.close)
        
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
        fs2_path = center.settings['fs2_path']
        fs2_bin = center.settings['fs2_bin']

        self.win.build.clear()

        if fs2_path is not None and os.path.isdir(fs2_path):
            fs2_path = os.path.abspath(fs2_path)
            bins = glob.glob(os.path.join(fs2_path, 'fs2_open_*'))
            
            idx = 0
            for path in bins:
                path = os.path.basename(path)

                if not path.endswith(('.map', '.pdb')):
                    self.win.build.addItem(path)
                    
                    if path == fs2_bin:
                        self.win.build.setCurrentIndex(idx)

                    idx += 1
            
            if len(bins) == 1:
                # Found only one binary, select it by default.
                self.win.build.setEnabled(False)
                self.save_build()

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
        self.win.vid_res.clear()

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
        self.win.vid_depth.clear()
        self.win.vid_depth.addItems(['32-bit', '16-bit'])

        index = self.win.vid_depth.findText('{0}-bit'.format(depth))
        if index != -1:
            self.win.vid_depth.setCurrentIndex(index)

        # Texture filter
        self.win.vid_texfilter.clear()
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
        self.win.vid_aa.clear()
        self.win.vid_aa.addItems(['Off', '2x', '4x', '8x', '16x'])

        index = self.win.vid_aa.findText('{0}x'.format(aa))
        if index == -1:
            index = 0
        self.win.vid_aa.setCurrentIndex(index)

        # Anisotropic filtering
        self.win.vid_af.clear()
        self.win.vid_af.addItems(['Off', '1x', '2x', '4x', '8x', '16x'])

        index = self.win.vid_af.findText('{0}x'.format(af))
        if index == -1:
            index = 0
        self.win.vid_af.setCurrentIndex(index)

        # ---Sound settings---
        if clibs.can_detect_audio():
            snd_devs, snd_default, snd_captures, snd_default_capture = clibs.list_audio_devs()
            self.win.snd_playback.clear()
            self.win.snd_capture.clear()

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
        
        self.win.ctrl_joystick.clear()
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
        
        #---Keyboard settings---
        if sys.platform.startswith('linux'):
            kls = self.win.keyLayoutSelect
            kls.clear()
            for i, layout in enumerate(('default (qwerty)', 'qwertz', 'azerty')):
                kls.addItem(layout)
                if layout == center.settings['keyboard_layout']:
                    kls.setCurrentIndex(i)

            if center.settings['keyboard_setxkbmap']:
                self.win.setxkbmapCheck.setChecked(True)
            else:
                self.win.setxkbmapCheck.setChecked(False)
        else:
            self.win.keyboardLabel.hide()
            for i in range(self.win.keyboardForm.count()):
                self.win.keyboardForm.itemAt(i).widget().hide()

        #---Network settings---
        self.win.net_type.clear()
        self.win.net_type.addItems(['None', 'Dialup', 'Broadband/LAN'])
        net_connections_read = {'none': 0, 'dialup': 1, 'LAN': 2}
        if net_connection in net_connections_read:
            index = net_connections_read[net_connection]
        else:
            index = 2
             
        self.win.net_type.setCurrentIndex(index)

        self.win.net_speed.clear()
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

        # keyboard
        if sys.platform.startswith('linux'):
            key_layout = self.win.keyLayoutSelect.currentIndex()
            if key_layout == 0:
                key_layout = 'default'
            else:
                key_layout = self.win.keyLayoutSelect.itemText(key_layout)

            center.settings['keyboard_layout'] = key_layout
            center.settings['keyboard_setxkbmap'] = self.win.setxkbmapCheck.isChecked()
        
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
        api.save_settings()

    def save_build(self):
        fs2_bin = str(self.win.build.currentText())
        if not os.path.isfile(os.path.join(center.settings['fs2_path'], fs2_bin)):
            return

        center.settings['fs2_bin'] = fs2_bin
        api.get_fso_flags()
        api.save_settings()

    def run_mod(self):
        logging.info('Launching...')
        
        self.write_config()

        if self.mod is not None:
            self.win.close()
            api.run_mod(self.mod)
        else:
            api.run_fs2()
    
    def show_flagwin(self):
        FlagsWindow(self.win, self.mod)


class SettingsTab(SettingsWindow):

    def __init__(self, tab):
        super(SettingsWindow, self).__init__()

        self.mod = None
        self.win = util.init_ui(Ui_Settings(), tab)

        self.win.browseButton.clicked.connect(api.select_fs2_path)
        
        self.win.cmdButton.setText('Default command line flags')
        self.win.cmdButton.clicked.connect(self.show_flagwin)
        self.read_config()
        
        self.win.build.activated.connect(self.save_build)
        self.win.runButton.clicked.connect(self.run_mod)
        self.win.saveButton.clicked.connect(self.write_config)
        self.win.cancelButton.hide()
        
        self.open()
