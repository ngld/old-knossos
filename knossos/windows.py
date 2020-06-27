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
import logging
import functools
import json
import threading
import datetime

from . import uhf
uhf(__name__)

from . import center, util, integration, web, repo, ipc, nebula
from .qt import QtCore, QtWidgets, load_styles
from .ui.hell import Ui_MainWindow as Ui_Hell
from .ui.install import Ui_InstallDialog
from .ui.install_update import Ui_InstallUpdateDialog
from .ui.edit_description import Ui_Dialog as Ui_DescEditor
from .tasks import run_task, InstallTask, UpdateTask, UninstallTask, WindowsUpdateTask, MacUpdateTask, LoadLocalModsTask

# Keep references to all open windows to prevent the GC from deleting them.
_open_wins = []
translate = QtCore.QCoreApplication.translate


class QDialog(QtWidgets.QDialog):

    def __init__(self, *args):
        super(QDialog, self).__init__(*args)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)


class QMainWindow(QtWidgets.QMainWindow):
    _drag_start = None
    _pos_start = None
    _size_start = None
    _drag = False
    _resize = None
    _custom_bar = False

    def __init__(self, custom_bar=False, *args):
        super(QMainWindow, self).__init__(*args)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.set_custom_bar(custom_bar)

    def set_custom_bar(self, enabled):
        if enabled != self._custom_bar:
            self.setWindowFlag(QtCore.Qt.FramelessWindowHint, enabled)
            self.setMouseTracking(enabled)
            self.hide()
            self.show()
            self._custom_bar = enabled

    def closeEvent(self, e):
        if center.pmaster.is_busy():
            e.ignore()

            box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'Knossos',
                'Some tasks are still running in the background. Please wait for them to finish or abort them.\n' +
                'If you force Knossos to quit, it might result in a corrupt mod installation or broken mod upload ' +
                '(depending on what Knossos is doing right now).',
                QtWidgets.QMessageBox.Ok)

            box.addButton('Force Quit', QtWidgets.QMessageBox.RejectRole)

            if box.exec_() == QtWidgets.QDialog.Rejected:
                center.app.quit()
        else:
            e.accept()
            center.app.quit()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.ActivationChange:
            if integration.current is not None:
                integration.current.annoy_user(False)

            if center.main_win and center.main_win.win.isActiveWindow() and center.auto_fetcher:
                center.auto_fetcher.trigger()

        return super(QMainWindow, self).changeEvent(event)

    def mousePressEvent(self, event):
        if self._custom_bar and event.button() == QtCore.Qt.LeftButton:
            self._drag_start = event.globalPos()
            self._pos_start = self.pos()
            self._size_start = self.size()
            event.accept()

            x = event.x()
            y = event.y()
            w = self.width()
            h = self.height()

            left = x < 6
            right = x > w - 6
            top = y < 6
            bottom = y > h - 6

            if left or right or top or bottom:
                rw = 0
                rh = 0

                if left:
                    rw = -1
                elif right:
                    rw = 1

                if top:
                    rh = -1
                elif bottom:
                    rh = 1

                self._drag = False
                self._resize = (rw, rh)
            elif y < 50:
                self._resize = (0, 0)
                self._drag = True

    def mouseDoubleClickEvent(self, event):
        if self._custom_bar and event.y() < 50:
            event.accept()
            self.setWindowState(self.windowState() ^ QtCore.Qt.WindowMaximized)

    def mouseReleaseEvent(self, event):
        self._drag = False
        self._resize = None
        self._drag_start = None

    def mouseMoveEvent(self, event):
        if self._custom_bar:
            if self._drag:
                self.move(event.globalPos() - self._drag_start + self._pos_start)
                event.accept()
            elif self._resize:
                diff = event.globalPos() - self._drag_start
                size = self._size_start * 1  # copy
                pos = self._pos_start * 1  # copy

                if self._resize[0] != 0:
                    size.setWidth(size.width() + (diff.x() * self._resize[0]))

                if self._resize[1] != 0:
                    size.setHeight(size.height() + (diff.y() * self._resize[1]))

                self.resize(size)
                size_diff = self.size() - self._size_start

                if self._resize[0] < 0:
                    pos.setX(pos.x() - size_diff.width())

                if self._resize[1] < 1:
                    pos.setY(pos.y() - size_diff.height())

                self.move(pos)
            else:
                x = event.x()
                y = event.y()
                w = self.width()
                h = self.height()

                left = x < 6
                right = x > w - 6
                top = y < 6
                bottom = y > h - 6

                if left and top or right and bottom:
                    self.setCursor(QtCore.Qt.SizeFDiagCursor)
                elif left and bottom or right and top:
                    self.setCursor(QtCore.Qt.SizeBDiagCursor)
                elif left or right:
                    self.setCursor(QtCore.Qt.SizeHorCursor)
                elif top or bottom:
                    self.setCursor(QtCore.Qt.SizeVerCursor)
                else:
                    self.setCursor(QtCore.Qt.ArrowCursor)


class Window(QtCore.QObject):
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
    _init_done = False
    _prg_visible = False
    _explore_mod_list_cache = None
    _installed_mod_list_cache = None
    browser_ctrl = None
    progress_win = None

    def __init__(self, window=True):
        super(HellWindow, self).__init__(window)
        self._tasks = {}
        self._updating_mods = {}
        self._explore_mod_list_cache = {}
        self._installed_mod_list_cache = {}

        self._create_win(Ui_Hell, QMainWindow)
        self.browser_ctrl = web.BrowserCtrl(self.win.webView)
        self.win.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.win.titleBarAreaLayout.setContentsMargins(0, 0, 6, 0)
        self.win.centralWidget().setAttribute(QtCore.Qt.WA_MouseTracking, True)
        self.win.titleBarArea.setAttribute(QtCore.Qt.WA_MouseTracking, True)
        self.win.progressInfo.setAttribute(QtCore.Qt.WA_MouseTracking, True)
        self.win.cornerIcon.setAttribute(QtCore.Qt.WA_MouseTracking, True)
        self.win.titleBar.setAttribute(QtCore.Qt.WA_MouseTracking, True)

        self.win.minimizeButton.clicked.connect(
            lambda: self.win.setWindowState(QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive))
        self.win.maximizeButton.clicked.connect(self.toggle_win)
        self.win.restoreButton.clicked.connect(self.toggle_win)
        self.win.closeButton.clicked.connect(self.win.close)

        center.signals.update_avail.connect(self.ask_update)
        center.signals.task_launched.connect(self.watch_task)

        self.win.setWindowTitle(self.win.windowTitle() + ' ' + center.VERSION)
        self.win.titleBar.setText(self.win.windowTitle())
        self.win.progressInfo.hide()

        if center.settings['custom_bar']:
            self.show_bar()
        else:
            self.hide_bar()

        self.open()

    def hide_bar(self):
        self.win.titleBarArea.hide()
        self.win.set_custom_bar(False)

    def show_bar(self):
        self.win.titleBarArea.show()
        self.win.set_custom_bar(True)

        if self.win.windowState() & QtCore.Qt.WindowMaximized:
            self.win.maximizeButton.hide()
            self.win.restoreButton.show()
        else:
            self.win.maximizeButton.show()
            self.win.restoreButton.hide()

    def toggle_win(self):
        state = (self.win.windowState() ^ QtCore.Qt.WindowMaximized) | QtCore.Qt.WindowActive
        self.win.setWindowState(state)

        if state & QtCore.Qt.WindowMaximized:
            self.win.maximizeButton.hide()
            self.win.restoreButton.show()
        else:
            self.win.maximizeButton.show()
            self.win.restoreButton.hide()

    def _del(self):
        center.signals.update_avail.disconnect(self.ask_update)
        center.signals.task_launched.disconnect(self.watch_task)

        # Trying to free this object usually leads to memory corruption
        # See http://pyqt.sourceforge.net/Docs/PyQt5/gotchas.html#crashes-on-exit
        # Since this is the main window and should only be closed whenever the application exits, skipping this
        # won't lead to memory leaks.
        # super(HellWindow, self)._del()

    def start_init(self):
        self.browser_ctrl.load()

    def finish_init(self):
        if self._init_done:
            return

        self._init_done = True
        self._init_explore_mod_list_cache()
        run_task(LoadLocalModsTask())

        center.auto_fetcher.start()
        ipc.setup()

    def ask_update(self, version):
        # We only have an updater for windows.
        if sys.platform in ('win32', 'darwin'):
            msg = self.tr('There\'s an update available!\nDo you want to install Knossos %s now?') % str(version)
            buttons = QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            result = QtWidgets.QMessageBox.question(center.app.activeWindow(), 'Knossos', msg, buttons)
            if result == QtWidgets.QMessageBox.Yes:
                if sys.platform == 'win32':
                    run_task(WindowsUpdateTask())
                elif sys.platform == 'darwin':
                    run_task(MacUpdateTask())
        else:
            msg = self.tr('There\'s an update available!\nYou should update to Knossos %s.') % str(version)
            QtWidgets.QMessageBox.information(center.app.activeWindow(), 'Knossos', msg)

    def _get_sort_parameters(self):
        # Maybe I should add "Just " to the list?
        prefixes = ('the ', 'a ')

        def _build_sort_title(mod):
            title = mod['title']
            for p in prefixes:
                pl = len(p)
                if title[:pl].lower() == p:
                    title = title[pl:]
            return title.lower()

        min_date_str = datetime.date.min.strftime('%Y-%m-%d')

        def _build_sort_date(mod_date):
            return mod_date if mod_date else min_date_str

        def _build_sort_last_played(mod):
            return _build_sort_date(mod['last_played'])

        def _build_sort_last_released(mod):
            return _build_sort_date(mod['first_release'])

        def _build_sort_last_updated(mod):
            return _build_sort_date(mod['last_update'])

        sort_key_dict = {
            'alphabetical': _build_sort_title,
            'last_played': _build_sort_last_played,
            'last_released': _build_sort_last_released,
            'last_updated': _build_sort_last_updated
        }

        sort_key = sort_key_dict[center.sort_type]
        sort_reverse = center.sort_type != 'alphabetical'

        return sort_key, sort_reverse

    def search_mods(self, search_filter=None, ignore_retail_dependency=False):
        mods = None
        if search_filter is None:
            search_filter = self._mod_filter

        if search_filter in ('home', 'develop'):
            mods = center.installed.mods
        elif search_filter == 'explore':
            mods = center.mods.mods
        else:
            mods = {}

        # Now filter the mods.
        query = self._search_text
        result = []
        for mid, mvs in mods.items():
            if query in mvs[0].title.lower():
                mod = mvs[0]

                if mod.mtype == 'engine' and search_filter != 'develop':
                    if not center.settings['show_fso_builds']:
                        continue

                    mvs = [mv for mv in mvs if mv.satisfies_stability(center.settings['engine_stability'])]
                    if len(mvs) == 0:
                        mvs = mods[mid]

                    mod = mvs[0]

                installed_versions = {}
                for m in center.installed.mods.get(mid, []):
                    installed_versions[str(m.version)] = m

                if str(mod.version) in installed_versions:
                    item = installed_versions[str(mod.version)].get()
                else:
                    item = mod.get()

                last_playeds = [mod.get_user()['last_played'] for mod in installed_versions.values()]
                last_playeds = sorted(list(filter(lambda lp: lp is not None, last_playeds)), reverse=True)
                item['last_played'] = last_playeds[0] if len(last_playeds) > 0 else None

                if mod.parent == 'FS2' and not center.installed.has('FS2') and not ignore_retail_dependency:
                    if center.settings['show_fs2_mods_without_retail']:
                        item['retail_dependency_missing'] = True
                    else:
                        continue
                else:
                    item['retail_dependency_missing'] = False

                item['progress'] = 0
                item['progress_info'] = {}

                rmod = center.mods.mods.get(mid, [])
                if mod.mtype == 'engine':
                    rm_sel = None
                    for m in rmod:
                        if m.stability == center.settings['engine_stability']:
                            rm_sel = m
                            break

                    if rm_sel:
                        rmod = rm_sel
                    elif len(rmod) > 0:
                        rmod = rmod[0]
                elif len(rmod) > 0:
                    rmod = rmod[0]

                # TODO: Refactor (see also templates/kn-{details,devel}-page.vue)
                if rmod and (rmod.version > mod.version or rmod.last_update != mod.last_update):
                    item['status'] = 'update'
                elif mod.mid in self._updating_mods:
                    item['status'] = 'updating'
                    item['progress'] = self._updating_mods[mod.mid]
                else:
                    item['status'] = 'ready'

                    if search_filter == 'home':
                        for pkg in mod.packages:
                            if pkg.files_checked > 0 and pkg.files_ok < pkg.files_checked:
                                item['status'] = 'error'
                                break

                item['installed'] = len(installed_versions) > 0
                item['versions'] = []
                for mod in mvs:
                    if str(mod.version) in installed_versions:
                        mv = installed_versions[str(mod.version)].get()
                        mv['installed'] = True
                    else:
                        mv = mod.get()
                        mv['installed'] = False
                        mv['dev_mode'] = False

                    if self._mod_filter != 'develop':
                        del mv['packages']

                    item['versions'].append(mv)

                if item['installed'] and not item['versions'][0]['installed']:
                    item['status'] = 'update'

                if self._mod_filter != 'develop':
                    del item['packages']

                result.append(item)

        sort_key, sort_reverse = self._get_sort_parameters()
        result.sort(key=sort_key, reverse=sort_reverse)
        return result, search_filter

    def _compute_mod_list_diff(self, new_mod_list):
        mod_list_cache = None
        if self._mod_filter in ('home', 'develop'):
            mod_list_cache = self._installed_mod_list_cache
        elif self._mod_filter == 'explore':
            mod_list_cache = self._explore_mod_list_cache
        else:
            raise Exception('_compute_mod_list_diff: unknown mod filter type %s' % self._mod_filter)

        updated_mods = {}
        for item in new_mod_list:
            old_item = mod_list_cache.get(item['id'], None)
            if item != old_item:
                updated_mods[item['id']] = item
                mod_list_cache[item['id']] = item

        return updated_mods

    def _init_explore_mod_list_cache(self):
        if center.settings['base_path'] is not None:
            explore_result, explore_filter = self.search_mods('explore', True)
            for item in explore_result:
                self._explore_mod_list_cache[item['id']] = item

    def get_explore_mod_list_cache_json(self):
        return json.dumps(self._explore_mod_list_cache)

    def update_mod_list(self):
        if center.settings['base_path'] is not None:
            result, filter_ = self.search_mods()

            if filter_ in ('home', 'explore', 'develop'):
                updated_mods = self._compute_mod_list_diff(result)
                mod_order = [item['id'] for item in result]

                self.browser_ctrl.bridge.updateModlist.emit(json.dumps(updated_mods), filter_, mod_order)

    def show_indicator(self):
        pass

    def update_mod_buttons(self, clicked=None):
        if center.settings['base_path'] is not None:
            self._mod_filter = clicked
            self.update_mod_list()

    def perform_search(self, term):
        self._search_text = term.lower()
        self.update_mod_list()

    def get_tasks(self):
        return self._tasks

    def watch_task(self, task):
        logging.debug('Task "%s" (%d, %s) started.', task.title, id(task), task.__class__)
        self._tasks[id(task)] = task
        self.browser_ctrl.bridge.taskStarted.emit(id(task), task.title, [m.mid for m in task.mods])

        for m in task.mods:
            self._updating_mods[m.mid] = 0

        task.done.connect(functools.partial(self._forget_task, task))
        task.progress.connect(functools.partial(self._track_progress, task))

        if len(task.mods) == 0 and not self._prg_visible:
            self._prg_visible = True
            self.win.progressInfo.show()
            self.win.progressLabel.setText(task.title)
            self.win.progressBar.setValue(0)

        integration.current.set_busy()

    def _track_progress(self, task, pi):
        self.browser_ctrl.bridge.taskProgress.emit(id(task), pi[0] * 100, json.dumps(pi[1]))

        for m in task.mods:
            self._updating_mods[m.mid] = pi[0] * 100

        if len(self._tasks) == 1 and pi[0] > 0:
            integration.current.set_progress(pi[0])

        if len(task.mods) == 0 and self._prg_visible:
            self.win.progressBar.setValue(pi[0] * 100)

    def _forget_task(self, task):
        tid = id(task)
        logging.debug('Task "%s" (%d) finished.', task.title, tid)
        self.browser_ctrl.bridge.taskFinished.emit(tid)
        if tid in self._tasks:
            del self._tasks[tid]

        for m in task.mods:
            if m.mid in self._updating_mods:
                del self._updating_mods[m.mid]

        if len(task.mods) == 0 and self._prg_visible:
            global_tasks = [t for t in self._tasks.values() if len(t.mods) == 0]
            if len(global_tasks) > 0:
                self.win.progressLabel.setText(global_tasks[0].title)
                self.win.progressBar.setValue(0)
                integration.current.set_busy()

            else:
                self._prg_visible = False
                self.win.progressInfo.hide()

        if len(self._tasks) == 0:
            integration.current.hide_progress()

    def abort_task(self, task):
        if task in self._tasks:
            self._tasks[task].abort()


class ModInstallWindow(Window):
    _window_cls = Ui_InstallDialog
    _mod = None
    _mod_ids = None
    _pkg_checks = None
    _dep_tpl = None
    _edit_thread = None
    updateEditable = QtCore.Signal(dict)

    def __init__(self, mod, sel_pkgs=[]):
        super(ModInstallWindow, self).__init__()

        self._mod = mod
        self._create_win(self._window_cls)
        self.win.splitter.setStretchFactor(0, 2)
        self.win.splitter.setStretchFactor(1, 1)

        self.label_tpl(self.win.titleLabel, MOD=mod.title)
        self.win.notesField.setPlainText(mod.notes)

        self._pkg_checks = []
        self.show_packages()
        self.update_deps()

        self.win.treeWidget.itemChanged.connect(self.update_selection)
        self.win.treeWidget.itemClicked.connect(self.update_notes)

        self.win.accepted.connect(self.install)
        self.win.rejected.connect(self.close)

        self.updateEditable.connect(self.update_editable)
        self._edit_thread = threading.Thread(target=self._check_editable, daemon=True)
        self._edit_thread.start()

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
        self._mod_ids = []
        for mod in mods:
            self._mod_ids.append((mod.mid, mod.version))
            item = QtWidgets.QTreeWidgetItem(self.win.treeWidget, ['%s %s' % (mod.title, mod.version), ''])
            item.setExpanded(True)
            item.setData(0, QtCore.Qt.UserRole, mod)
            item.setData(0, QtCore.Qt.UserRole + 2, '')
            c = 0

            try:
                local_mod = center.installed.query(mod)
            except repo.ModNotFound:
                local_mod = None

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
                is_required = len(center.installed.get_dependents([pkg])) > 0

                if is_installed:
                    sub.setText(1, self.tr('Installed'))

                if pkg.status == 'required' or pkg in needed_pkgs or is_required or (local_mod and local_mod.dev_mode):
                    sub.setCheckState(0, QtCore.Qt.Checked)
                    sub.setDisabled(True)

                    c += 1
                elif pkg.status == 'recommended':
                    if not local_mod or is_installed:
                        sub.setCheckState(0, QtCore.Qt.Checked)
                        c += 1
                    else:
                        sub.setCheckState(0, QtCore.Qt.Unchecked)

                elif pkg.status == 'optional':
                    if is_installed:
                        sub.setCheckState(0, QtCore.Qt.Checked)
                        c += 1
                    else:
                        sub.setCheckState(0, QtCore.Qt.Unchecked)

                sub.setData(0, QtCore.Qt.UserRole, pkg)
                sub.setData(0, QtCore.Qt.UserRole + 1, is_installed)
                sub.setData(0, QtCore.Qt.UserRole + 2, pkg.notes)
                self._pkg_checks.append(sub)

            if c == len(mod.packages):
                item.setCheckState(0, QtCore.Qt.Checked)
            elif c > 0:
                item.setCheckState(0, QtCore.Qt.PartiallyChecked)
            else:
                item.setCheckState(0, QtCore.Qt.Unchecked)

        self.win.treeWidget.header().resizeSections(QtWidgets.QHeaderView.ResizeToContents)

    def _check_editable(self):
        client = nebula.NebulaClient()
        res = {}
        for mid, version in self._mod_ids:
            try:
                inst_mod = center.installed.query(mid, version)
                res[mid] = (inst_mod.dev_mode, True)
                continue
            except repo.ModNotFound:
                pass

            if center.settings['neb_user']:
                try:
                    result = client.is_editable(mid)
                    res[mid] = (result['result'], False)
                except Exception:
                    logging.exception('Failed to retrieve editable status for %s!' % mid)
                    res[mid] = (False, False)
            else:
                res[mid] = (False, False)

        if not self.closed:
            self.updateEditable.emit(res)

    def update_editable(self, info):
        tree = self.win.treeWidget

        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            mid = item.data(0, QtCore.Qt.UserRole).mid

            if info[mid][0]:
                item.setCheckState(2, QtCore.Qt.Checked)
                item.setData(2, QtCore.Qt.UserRole, info[mid][1])

    def update_selection(self, item, col):
        obj = item.data(0, QtCore.Qt.UserRole)
        if isinstance(obj, repo.Mod):
            cs = item.checkState(0)

            if cs != QtCore.Qt.PartiallyChecked:
                for i in range(item.childCount()):
                    child = item.child(i)
                    if not child.isDisabled():
                        child.setCheckState(0, cs)

            if item.data(2, QtCore.Qt.UserRole) and item.checkState(2) != QtCore.Qt.Checked:
                item.setCheckState(2, QtCore.Qt.Checked)

        self.update_deps()

    def get_selected_pkgs(self):
        to_install = []
        to_remove = []
        editable = {}

        for item in self._pkg_checks:
            selected = item.checkState(0) == QtCore.Qt.Checked
            installed = item.data(0, QtCore.Qt.UserRole + 1)
            mod = item.data(0, QtCore.Qt.UserRole)

            if selected != installed:
                if installed:
                    to_remove.append(mod)
                else:
                    to_install.append(mod)

        for i in range(self.win.treeWidget.topLevelItemCount()):
            item = self.win.treeWidget.topLevelItem(i)
            mod = item.data(0, QtCore.Qt.UserRole)

            if item.checkState(2) == QtCore.Qt.Checked:
                editable[mod.mid] = True

        to_install = center.mods.process_pkg_selection(to_install)
        return to_install, to_remove, editable

    def update_deps(self):
        pkg_sel, rem_sel, editable = self.get_selected_pkgs()
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

    def update_notes(self, item):
        self.win.notesField.setPlainText(item.data(0, QtCore.Qt.UserRole + 2))

    def install(self):
        to_install, to_remove, editable = self.get_selected_pkgs()

        def follow_up():
            if to_remove:
                run_task(UninstallTask(to_remove, mods=[self._mod]))

        if to_install:
            t1 = run_task(InstallTask(to_install, self._mod, editable=editable, check_after=not to_remove))
            t1.done.connect(follow_up)
        else:
            follow_up()

        self.close()


class ModInstallUpdateWindow(ModInstallWindow):
    _window_cls = Ui_InstallUpdateDialog

    def __init__(self, mod, old_mod, sel_pkgs=None):
        super(ModInstallUpdateWindow, self).__init__(mod, sel_pkgs)
        self._old_mod = old_mod

    def _check_editable(self):
        # We just use the values from the previous version.
        pass

    def install(self):
        to_install, _, editable = self.get_selected_pkgs()

        if to_install:
            run_task(UpdateTask(self._old_mod, pkgs=to_install))

        self.close()


class DescriptionEditorWindow(Window):

    def __init__(self, text):
        super(DescriptionEditorWindow, self).__init__()

        self._create_win(Ui_DescEditor)
        self.win.descEdit.setPlainText(text)

        self.win.applyButton.clicked.connect(self.apply_text)
        self.win.cancelButton.clicked.connect(self.close)

        self.open()

    def apply_text(self):
        center.main_win.browser_ctrl.bridge.applyDevDesc.emit(self.win.descEdit.toPlainText())
        self.close()
