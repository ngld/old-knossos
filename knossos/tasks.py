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
import subprocess
import shutil
import glob
import stat
import json
import tempfile
import threading
import random
import time
import semantic_version

from . import center, util, progress, nebula, repo
from .repo import Repo
from .qt import QtCore, QtWidgets, read_file


translate = QtCore.QCoreApplication.translate


class FetchTask(progress.Task):

    def __init__(self):
        super(FetchTask, self).__init__()
        self.title = 'Fetching mod list...'

        # Remove all logos.
        for path in glob.glob(os.path.join(center.settings_path, 'logo*.*')):
            if os.path.isfile(path):
                logging.info('Removing old logo "%s"...', path)
                os.unlink(path)

        self.done.connect(self.finish)
        self.add_work([('repo', i * 100, link[0]) for i, link in enumerate(center.settings['repos'])])

    def work(self, params):
        if params[0] == 'repo':
            _, prio, link = params

            progress.update(0.1, 'Fetching "%s"...' % link)

            try:
                raw_data = util.get(link, raw=True)
                if not raw_data:
                    return

                data = Repo()
                data.is_link = True
                data.base = os.path.dirname(raw_data.url)
                data.parse(raw_data.text)
            except Exception:
                logging.exception('Failed to decode "%s"!', link)
                return

            wl = []
            for mid, mvs in data.mods.items():
                for mod in mvs:
                    wl.append(('mod', mod))

            self.add_work(wl)
            self.post((prio, data))
        else:
            mod = params[1]
            mod.save_logo(center.settings_path)

    def finish(self):
        if not self.aborted:
            modlist = center.mods = Repo()
            res = self.get_results()
            res.sort(key=lambda x: x[0])

            for part in res:
                modlist.merge(part[1])

            modlist.save_json(os.path.join(center.settings_path, 'mods.json'))
            center.save_settings()

        run_task(CheckTask())


class CheckTask(progress.MultistepTask):
    can_abort = False
    _steps = 2

    def __init__(self):
        super(CheckTask, self).__init__(threads=3)

        self.done.connect(self.finish)
        self.title = 'Checking installed mods...'

    def init1(self):
        if center.settings['base_path'] is None:
            logging.error('A CheckTask was launched even though no base path was set!')
        else:
            center.installed.clear()
            self.add_work((center.settings['base_path'],))
            self.add_work(center.settings['base_dirs'])

    def work1(self, path):
        mods = center.installed

        subs = []
        mod_file = None

        try:
            for base in os.listdir(path):
                sub = os.path.join(path, base)

                if os.path.isdir(sub):
                    subs.append(sub)
                elif base.lower() == 'mod.json':
                    mod_file = sub
        except FileNotFoundError:
            logging.warn('The directory "%s" does not exist anymore!' % path)

        if mod_file:
            try:
                mod = repo.InstalledMod.load(mod_file)
                mods.add_mod(mod)
            except Exception:
                logging.exception('Failed to parse "%s"!', sub)

        self.add_work(subs)

    def init2(self):
        pkgs = []
        for mid, mvs in center.installed.mods.items():
            for mod in mvs:
                pkgs.extend(mod.packages)

        # Reset them
        for pkg in pkgs:
            pkg.files_ok = 0
            pkg.files_checked = 0

        self.add_work(pkgs)

    def work2(self, pkg):
        mod = pkg.get_mod()
        pkg_files = pkg.filelist
        count = float(len(pkg_files))
        success = 0
        missing = 0
        checked = 0

        archives = set()
        msgs = []

        for info in pkg_files:
            mypath = util.ipath(os.path.join(mod.folder, info['filename']))
            fix = False
            if os.path.isfile(mypath):
                progress.update(checked / count, 'Checking "%s"...' % (info['filename']))

                if util.check_hash(info['checksum'], mypath):
                    success += 1
                else:
                    msgs.append('File "%s" is corrupted. (checksum mismatch)' % (info['filename']))
                    fix = True
            else:
                msgs.append('File "%s" is missing.' % (info['filename']))
                missing += 1
                fix = True

            if fix:
                archives.add(info['archive'])

            checked += 1

        self.post((pkg, archives, success, missing, checked, msgs))

    def finish(self):
        results = self.get_results()

        # Make sure that the calculated checksums are saved.
        center.save_settings()

        for pkg, archives, s, m, c, msg in results:
            mod = pkg.get_mod()

            if s == 0:
                if m > 0:
                    # Not Installed
                    # What?!
                    logging.warning('Package %s of mod %s (%s) is not installed but in the local repo. Fixing...' % (pkg.name, mod.mid, mod.title))
                    mod.del_pkg(pkg)
                    mod.save()
                elif c > 0:
                    logging.warning('Package %s of mod %s (%s) is completely corrupted!!' % (pkg.name, mod.mid, mod.title))

            if pkg is not None:
                pkg.check_notes = msg
                pkg.files_ok = s
                pkg.files_checked = c

        center.signals.repo_updated.emit()


class CheckFilesTask(progress.MultistepTask):
    can_abort = False
    _mod = None
    _check_results = None
    _steps = 2

    def __init__(self, mod):
        super(CheckFilesTask, self).__init__(threads=3)

        self.title = 'Checking "%s"...' % mod.title
        self.mods = [mod]
        self._mod = mod

    def init1(self):
        modpath = self._mod.folder
        pkgs = []

        for pkg in self._mod.packages:
            pkgs.append((modpath, pkg))

        self.add_work(pkgs)

    def work1(self, data):
        modpath, pkg = data
        pkg_files = pkg.filelist
        count = float(len(pkg_files))
        success = 0
        checked = 0

        summary = {
            'ok': [],
            'corrupt': [],
            'missing': []
        }

        for info in pkg_files:
            mypath = util.ipath(os.path.join(modpath, info['filename']))
            if os.path.isfile(mypath):
                progress.update(checked / count, 'Checking "%s"...' % (info['filename']))

                if util.check_hash(info['checksum'], mypath):
                    success += 1
                    summary['ok'].append(info['filename'])
                else:
                    summary['corrupt'].append(info['filename'])
            else:
                summary['missing'].append(info['filename'])

            checked += 1

        self.post((pkg, success, checked, summary))

    def init2(self):
        # Save the results from step 1.
        self._check_results = self.get_results()

        self.add_work(('',))

    def work2(self, d):
        modpath = self._mod.folder
        fnames = set()
        loose = []

        # Collect all filenames
        for pkg, s, c, m in self._check_results:
            for info in pkg.filelist:
                fnames.add(info['filename'])

        # Ignore files are generated by Knossos
        fnames.add('mod.json')

        # Check for loose files.
        for path, dirs, files in os.walk(modpath):
            if path == modpath:
                subpath = ''
            else:
                subpath = os.path.relpath(path, modpath)

            for item in files:
                name = os.path.join(subpath, item).replace('\\', '/')
                if name not in fnames and not name.startswith(('__k_plibs', 'knossos.')):
                    loose.append(name)

        self._check_results.append((None, 0, 0, {'loose': loose}))
        self._results = self._check_results


# TODO: Optimize, make sure all paths are relative (no mod should be able to install to C:\evil)
# TODO: Add error messages.
class InstallTask(progress.MultistepTask):
    _pkgs = None
    _pkg_names = None
    _mods = None
    _dls = None
    _steps = 2
    _error = False
    _7z_lock = None
    _pkg_prog = None
    check_after = True

    def __init__(self, pkgs, mod=None, check_after=True):
        super(InstallTask, self).__init__()

        self._mods = set()
        self._pkgs = []
        self._pkg_names = []
        self._pkg_prog = {}
        self._local = threading.local()
        self.check_after = check_after

        if sys.platform == 'win32':
            self._7z_lock = threading.Lock()

        if mod is not None:
            self.mods = [mod]

        for pkg in pkgs:
            ins_pkg = center.installed.add_pkg(pkg)
            pmod = ins_pkg.get_mod()
            self._pkgs.append(ins_pkg)
            self._mods.add(pmod)
            self._pkg_names.append((pmod.mid, ins_pkg.name))

        for m in self._mods:
            if m not in self.mods:
                self.mods.append(m)

        center.signals.repo_updated.emit()
        self.done.connect(self.finish)
        self.title = 'Installing mods...'

    def _track_progress(self, prog, text):
        with self._progress_lock:
            if self._local.pkg:
                self._pkg_prog[self._local.pkg] = (self._pkg_prog[self._local.pkg][0], prog, text)

            total = 0
            for label, prog, text in self._pkg_prog.values():
                total += prog

            self.progress.emit((total / max(1, len(self._pkg_prog)), self._pkg_prog, 'Installing mods...'))

    def abort(self):
        super(InstallTask, self).abort()

        util.cancel_downloads()

    def finish(self):
        if self.aborted:
            if self._cur_step == 1:
                # Need to remove all those temporary directories.
                for ar in self.get_results():
                    try:
                        shutil.rmtree(ar['tpath'])
                    except Exception:
                        logging.exception('Failed to remove "%s"!' % ar['tpath'])
        elif self._error:
            msg = self.tr(
                'An error occured during the installation of a mod. It might be partially installed.\n' +
                'If you need more help, ask ngld or read the debug log!'
            )
            QtWidgets.QMessageBox.critical(None, 'Knossos', msg)
        else:
            # Generate mod.json files.
            for mod in self._mods:
                try:
                    # Make sure the images are in the mod folder so that they won't be deleted during the next
                    # FetchTask.
                    for prop in ('logo', 'tile'):
                        img_path = getattr(mod, prop + '_path')
                        if img_path:
                            ext = os.path.splitext(img_path)[1]
                            dest = os.path.join(mod.folder, 'kn_' + prop + ext)

                            shutil.copyfile(img_path, dest)
                            setattr(mod, prop + '_path', dest)

                    mod.save()
                    util.get(center.settings['nebula_link'] + 'api/1/track/install/' + mod.mid)
                except Exception:
                    logging.exception('Failed to generate mod.json file for %s!' % mod.mid)

        if self.check_after:
            run_task(CheckTask())

    def init1(self):
        self._threads = 3
        self.add_work(self._mods)

    def work1(self, mod):
        modpath = mod.folder
        mfiles = mod.get_files()
        mnames = [f['filename'] for f in mfiles] + ['knossos.bmp', 'mod.json']
        self._local.pkg = None

        archives = set()
        progress.update(0, 'Checking %s...' % mod.title)

        kpath = os.path.join(modpath, 'mod.json')
        if os.path.isfile(kpath):
            try:
                with open(kpath, 'r') as stream:
                    info = json.load(stream)
            except Exception:
                logging.exception('Failed to parse mod.json!')
                info = None

            if info is not None and info['version'] != str(mod.version):
                # TODO: Remove old files
                logging.info('Overwriting "%s" (%s) with version %s.' % (mod.mid, info['version'], mod.version))

        if os.path.isdir(modpath):
            for path, dirs, files in os.walk(modpath):
                relpath = path[len(modpath):].lstrip('/\\')
                for item in files:
                    itempath = util.pjoin(relpath, item)
                    if not itempath.startswith('__k_plibs') and itempath not in mnames:
                        logging.info('File "%s" is left over.', itempath)
        else:
            logging.debug('Folder %s for %s does not yet exist.', mod, modpath)

        amount = float(len(mfiles))
        for i, info in enumerate(mfiles):
            if (mod.mid, info['package']) not in self._pkg_names:
                continue

            progress.update(i / amount, 'Checking %s: %s...' % (mod.title, info['filename']))

            itempath = util.ipath(os.path.join(modpath, info['filename']))
            if not os.path.isfile(itempath) or util.check_hash(info['checksum'], itempath):
                archives.add((mod.mid, info['package'], info['archive']))
                logging.debug('%s is missing for %s.', itempath, mod)

        self.post(archives)

    def init2(self):
        archives = set()
        downloads = []

        for a in self.get_results():
            archives |= a

        for pkg in self._pkgs:
            mod = pkg.get_mod()
            for item in pkg.files.values():
                if (mod.mid, pkg.name, item['filename']) in archives:
                    item = item.copy()
                    item['mod'] = mod
                    item['pkg'] = pkg
                    downloads.append(item)

                    self._pkg_prog[id(item)] = ('%s: %s' % (mod.title, item['filename']), 0, 'Checking...')

        if len(archives) == 0:
            logging.info('Nothing to do for this InstallTask!')
        elif len(downloads) == 0:
            logging.error('Somehow we didn\'t find any downloads for this InstallTask!')
            self._error = True

        self._threads = 0
        self.add_work(downloads)

    def work2(self, archive):
        self._local.pkg = id(archive)

        with tempfile.TemporaryDirectory() as tpath:
            arpath = os.path.join(tpath, archive['filename'])
            modpath = archive['mod'].folder

            # TODO: Maybe this should be an option?
            retries = 3
            done = False
            urls = list(archive['urls'])
            random.shuffle(urls)

            while retries > 0:
                retries -= 1

                for url in urls:
                    progress.start_task(0, 0.97, '%s')
                    progress.update(0, 'Ready')

                    with open(arpath, 'wb') as stream:
                        if not util.download(url, stream):
                            if self.aborted:
                                return

                            logging.error('Download of "%s" failed!', url)
                            continue

                    progress.finish_task()
                    progress.update(0.97, 'Checking "%s"...' % archive['filename'])

                    if util.check_hash(archive['checksum'], arpath):
                        done = True
                        retries = 0
                        break
                    else:
                        logging.error('File "%s" is corrupted!', url)

            if not done:
                logging.error('Missing file "%s"!', archive['filename'])
                self._error = True
                return

            if self.aborted:
                return

            if archive['is_archive']:
                cpath = os.path.join(tpath, 'content')
                os.mkdir(cpath)

                needed_files = filter(lambda item: item['archive'] == archive['filename'], archive['pkg'].filelist)
                done = False

                if sys.platform == 'win32':
                    # Apparently I can't run multiple 7z instances on Windows. If I do, I always get the error
                    # "The archive can't be opened because it is still in use by another process."
                    # I have no idea why. It works fine on Linux and Mac OS.
                    # TODO: Is there a better solution?

                    progress.update(0.98, 'Waiting...')
                    self._7z_lock.acquire()

                progress.update(0.98, 'Extracting %s...' % archive['filename'])
                logging.debug('Extracting %s into %s', archive['filename'], modpath)

                if util.extract_archive(arpath, cpath):
                    done = True
                    # Look for missing files
                    for item in needed_files:
                        src_path = os.path.join(cpath, item['orig_name'])

                        if not os.path.isfile(src_path):
                            logging.warning('Missing file "%s" from archive "%s" for package "%s" (%s)!',
                                            item['orig_name'], archive['filename'], archive['pkg'].name, archive['mod'].title)

                            done = False
                            break

                if sys.platform == 'win32':
                    self._7z_lock.release()

                if not done:
                    logging.error('Failed to unpack archive "%s" for package "%s" (%s)!',
                                  archive['filename'], archive['pkg'].name, archive['mod'].title)
                    shutil.rmtree(cpath, ignore_errors=True)
                    self._error = True
                    return

                for item in archive['pkg'].filelist:
                    if item['archive'] != archive['filename']:
                        continue

                    src_path = os.path.join(cpath, item['orig_name'])
                    dest_path = util.ipath(os.path.join(modpath, item['filename']))

                    try:
                        dparent = os.path.dirname(dest_path)
                        if not os.path.isdir(dparent):
                            os.makedirs(dparent)

                        # This move might fail on Windows with Permission Denied errors.
                        # "[WinError 32] The process cannot access the file because it is being used by another process"
                        # Just try it again several times to account of AV scanning and similar problems.
                        tries = 5
                        while tries > 0:
                            try:
                                shutil.move(src_path, dest_path)
                                break
                            except Exception as e:
                                logging.warning('Initial move for "%s" failed (%s)!' % (src_path, str(e)))
                                tries -= 1

                                if tries == 0:
                                    raise
                                else:
                                    time.sleep(1)
                    except Exception:
                        logging.exception('Failed to move file "%s" from archive "%s" for package "%s" (%s) to its destination %s!',
                                          src_path, archive['filename'], archive['pkg'].name, archive['mod'].title, dest_path)
                        self._error = True

                # Copy the remaining empty dirs and symlinks.
                for path, dirs, files in os.walk(cpath):
                    path = os.path.relpath(path, cpath)

                    for name in dirs:
                        src_path = os.path.join(cpath, path, name)
                        dest_path = util.ipath(os.path.join(modpath, path, name))

                        if os.path.islink(src_path):
                            if not os.path.lexists(dest_path):
                                linkto = os.readlink(src_path)
                                os.symlink(linkto, dest_path)
                        elif not os.path.exists(dest_path):
                            os.makedirs(dest_path)

                    for name in files:
                        src_path = os.path.join(cpath, path, name)

                        if os.path.islink(src_path):
                            dest_path = util.ipath(os.path.join(modpath, path, name))
                            if not os.path.lexists(dest_path):
                                linkto = os.readlink(src_path)
                                os.symlink(linkto, dest_path)
            else:
                for item in archive['pkg'].filelist:
                    if item['archive'] != archive['filename']:
                        continue

                    dest_path = util.ipath(os.path.join(modpath, archive['filename']))

                    try:
                        dparent = os.path.dirname(dest_path)
                        if not os.path.isdir(dparent):
                            os.makedirs(dparent)

                        tries = 3
                        while tries > 0:
                            try:
                                shutil.move(arpath, dest_path)
                                break
                            except Exception as e:
                                logging.warning('Initial move for "%s" failed (%s)!' % (src_path, str(e)))
                                tries -= 1

                                if tries == 0:
                                    raise
                                else:
                                    time.sleep(1)
                    except Exception:
                        logging.exception('Failed to move file "%s" from archive "%s" for package "%s" (%s) to its destination %s!',
                                          arpath, archive['filename'], archive['pkg'].name, archive['mod'].title, dest_path)
                        self._error = True

            progress.update(1, 'Done.')


# TODO: make sure all paths are relative (no mod should be able to install to C:\evil)
class UninstallTask(progress.MultistepTask):
    _pkgs = None
    _mods = None
    _steps = 2
    check_after = True

    def __init__(self, pkgs, check_after=True, mods=[]):
        super(UninstallTask, self).__init__()

        self._pkgs = []
        self._mods = mods
        self.check_after = check_after

        for pkg in pkgs:
            try:
                self._pkgs.append(center.installed.query(pkg))
            except repo.ModNotFound:
                logging.exception('Someone tried to uninstall a non-existant package (%s, %s)! Skipping it...', pkg.get_mod().mid, pkg.name)

        self.done.connect(self.finish)
        self.title = 'Uninstalling mods...'

    def init1(self):
        self.add_work(self._pkgs)

    def work1(self, pkg):
        mod = pkg.get_mod()

        for item in pkg.filelist:
            path = util.ipath(os.path.join(mod.folder, item['filename']))
            if not os.path.isfile(path):
                logging.warning('File "%s" for mod "%s" (%s) is missing during uninstall!', item['filename'], mod.title, mod.mid)
            else:
                os.unlink(path)

    def init2(self):
        mods = set(self._mods)

        # Unregister uninstalled pkgs.
        for pkg in self._pkgs:
            mods.add(pkg.get_mod())
            center.installed.del_pkg(pkg)

        self.add_work(mods)

    def work2(self, mod):
        modpath = mod.folder

        try:
            if isinstance(mod, repo.IniMod):
                shutil.rmtree(modpath)
            elif len(mod.packages) == 0:
                # Remove our files

                my_files = (os.path.join(modpath, 'mod.json'), mod.logo_path)
                for path in my_files:
                    if path and os.path.isfile(path):
                        os.unlink(path)

                libs = os.path.join(modpath, '__k_plibs')
                if os.path.isdir(libs):
                    # Delete any symlinks before running shutil.rmtree().
                    for link in os.listdir(libs):
                        item = os.path.join(libs, link)
                        if os.path.islink(item):
                            os.unlink(item)

                    shutil.rmtree(libs)

                center.installed.del_mod(mod)
            else:
                mod.save()
        except Exception:
            logging.exception('Failed to uninstall mod from "%s"!' % modpath)
            self._error = True

        # Remove empty directories.
        for path, dirs, files in os.walk(modpath, topdown=False):
            if len(dirs) == 0 and len(files) == 0:
                os.rmdir(path)

    def finish(self):
        if self.check_after:
            run_task(CheckTask())


class UpdateTask(InstallTask):
    _old_mod = None
    _new_mod = None
    _new_modpath = None
    __check_after = True

    def __init__(self, mod, check_after=True):
        self._old_mod = mod
        self._new_mod = center.mods.query(mod.mid)
        self.__check_after = check_after

        old_pkgs = [pkg.name for pkg in mod.packages]
        pkgs = []

        for pkg in self._new_mod.packages:
            if pkg.name in old_pkgs or pkg.status == 'required':
                pkgs.append(pkg)

        super(UpdateTask, self).__init__(pkgs, self._new_mod, check_after=False)

    def finish(self):
        self._new_modpath = self._new_mod.folder
        super(UpdateTask, self).finish()

        if not self.aborted and not self._error:
            # TODO: Check if it's okay to uninstall the old version. Maybe there's still a mod that requires this one?
            # The new version has been succesfully installed, remove the old version.
            next_task = UninstallTask(self._old_mod.packages, check_after=False)
            next_task.done.connect(self._finish2)
            run_task(next_task)

    def _finish2(self):
        modpath = self._old_mod.folder
        temppath = self._new_modpath

        if '_kv_' not in modpath:
            # Move all files from the temporary directory to the new one.
            try:
                if not os.path.isdir(modpath):
                    os.makedirs(modpath)

                for item in os.listdir(temppath):
                    shutil.move(os.path.join(temppath, item), os.path.join(modpath, item))
            except Exception:
                logging.exception('Failed to move a file!')
                QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr(
                    'Failed to replace the old mod files with the updated files!'))

                if self.__check_after:
                    run_task(CheckTask())
                return

            try:
                # Remove the now empty temporary folder
                os.rmdir(temppath)
            except Exception:
                logging.warning('Failed to remove supposedly empty folder "%s"!', temppath, exc_info=True)

        if self.__check_after:
            run_task(CheckTask())


class UploadTask(progress.MultistepTask):
    can_abort = True
    _steps = 2
    _client = None
    _mod = None
    _dir = None
    _login_failed = False
    _reason = None
    _success = False
    _msg_table = {
        'invalid version': 'the version number specified for this release is invalid!',
        'outdated version': 'there is already a release with the same or newer version on the nebula.',
        'unsupported archive checksum': 'your client sent an invalid checksum. You probably need to update.',
        'archive missing': 'one of your archives failed to upload.'
    }

    def __init__(self, mod):
        super(UploadTask, self).__init__()

        self.title = 'Uploading mod...'
        self.mods = [mod]
        self._mod = mod.copy()

        self._threads = 2
        self._local = threading.local()
        self._slot_prog = {
            'total': ('Status', 0, 'Waiting...')
        }

        self.done.connect(self.finish)

    def _track_progress(self, prog, text):
        with self._progress_lock:
            if self._local.slot:
                self._slot_prog[self._local.slot] = (self._slot_prog[self._local.slot][0], prog, text)

            total = 0
            for label, prog, text in self._slot_prog.values():
                total += prog

            self.progress.emit((total / max(1, len(self._slot_prog)), self._slot_prog, 'Uploading mod...'))

    def init1(self):
        self._local.slot = 'total'

        try:
            progress.update(0.1, 'Logging in...')

            self._dir = tempfile.TemporaryDirectory()
            self._client = client = nebula.NebulaClient()

            try:
                mods = client.get_editable_mods()
            except nebula.InvalidLoginException:
                self._login_failed = True
                self.abort()

                progress.update(0.1, 'Failed to login!')
                return

            progress.update(0.11, 'Updating metadata...')

            if self._mod.mid not in mods:
                client.create_mod(self._mod)
            else:
                client.update_mod(self._mod)

            progress.update(0.13, 'Performing pre-flight checks...')
            client.preflight_release(self._mod)

            progress.update(0.15, 'Scanning files...')
            archives = []
            for pkg in self._mod.packages:
                ar_name = pkg.name + '.7z'
                pkg_path = os.path.join(self._mod.folder, pkg.folder)
                pkg.filelist = []

                for sub, dirs, files in os.walk(pkg_path):
                    relsub = os.path.relpath(sub, pkg_path)
                    for fn in files:
                        path = os.path.join(sub, fn)
                        relpath = os.path.join(relsub, fn)

                        pkg.filelist.append({
                            'filename': relpath,
                            'archive': ar_name,
                            'orig_name': relpath,
                            'checksum': util.gen_hash(path)
                        })

                archives.append(pkg)
                self._slot_prog[pkg.name] = (pkg.name + '.7z', 0, 'Waiting...')

            progress.update(0.2, 'Uploading...')
            self.add_work(archives)
        except nebula.AccessDeniedException:
            self._reason = 'unauthorized'
            self.abort()
        except nebula.RequestFailedException as exc:
            if exc.args[0] not in self._msg_table:
                logging.exception('Failed request to nebula during upload!')

            self._reason = exc.args[0]
            self.abort()
            return

    def work1(self, pkg):
        self._local.slot = pkg.name

        try:
            progress.update(0, 'Packing...')

            ar_name = pkg.name + '.7z'
            ar_path = os.path.join(self._dir.name, ar_name)

            rc = util.call([util.SEVEN_PATH, 'a', ar_path, '.'], cwd=os.path.join(self._mod.folder, pkg.folder))
            if rc != 0:
                logging.error('Failed to build %s!' % ar_name)
                self.abort()
                return

            progress.start_task(0.1, 0.9, '%s')
            progress.update(0, 'Preparing upload...')

            pkg.files[ar_name] = {
                'filename': ar_name,
                'dest': '',
                'checksum': util.gen_hash(ar_path),
                'filesize': os.stat(ar_path).st_size,
                'is_archive': True
            }

            self._client.upload_file(ar_name, ar_path)
            progress.finish_task()
            progress.update(1, 'Done!')
        except nebula.RequestFailedException:
            logging.exception('Failed request to nebula during upload!')

            self._reason = 'archive missing'
            self.abort()

    def init2(self):
        self._local.slot = 'total'

        try:
            progress.update(0.8, 'Finishing...')
            self._client.create_release(self._mod)
            progress.update(1, 'Done')
            self._success = True
        except nebula.AccessDeniedException:
            self._reason = 'unauthorized'
            self.abort()

        except nebula.RequestFailedException as exc:
            if exc.args[0] not in self._msg_table:
                logging.exception('Failed request to nebula during upload!')

            self._reason = exc.args[0]
            self.abort()

    def work2(self):
        pass

    def finish(self):
        self._dir.cleanup()

        if self._login_failed:
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'Failed to login!')
        elif self._reason == 'unauthorized':
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'You are not authorized to edit this mod!')
        elif self._success:
            QtWidgets.QMessageBox.information(None, 'Knossos', 'Successfully uploaded mod!')
        elif self._reason in self._msg_table:
            QtWidgets.QMessageBox.critical(None, 'Knossos',
                "Your mod couldn't be uploaded because %s" % self._msg_table[self._reason])
        else:
            QtWidgets.QMessageBox.critical(None, 'Knossos', 'An unexpected error occured! Sorry...')


class GOGExtractTask(progress.Task):
    can_abort = False

    def __init__(self, gog_path, dest_path):
        super(GOGExtractTask, self).__init__()

        self.done.connect(self.finish)
        self.add_work([(gog_path, dest_path)])
        self.title = 'Installing FS2 from GOG...'

        if not center.installed.has('FSO'):
            try:
                fso = center.mods.query('FSO')
                run_task(InstallTask(fso.resolve_deps()))
            except repo.ModNotFound:
                logging.warn('Installing retail files but FSO is missing!')

    def work(self, paths):
        gog_path, dest_path = paths

        progress.update(0.03, 'Looking for InnoExtract...')
        data = util.get(center.INNOEXTRACT_LINK)

        try:
            data = json.loads(data)
        except Exception:
            logging.exception('Failed to read JSON data!')
            return

        link = None
        path = None
        for plat, info in data.items():
            if sys.platform.startswith(plat):
                link, path = info[:2]
                break

        if link is None:
            logging.error('Couldn\'t find an innoextract download for "%s"!', sys.platform)
            return

        if not os.path.exists(dest_path):
            os.makedirs(dest_path)

        inno = os.path.join(dest_path, os.path.basename(path))
        with tempfile.TemporaryDirectory() as tempdir:
            archive = os.path.join(tempdir, os.path.basename(link))

            progress.start_task(0.03, 0.10, 'Downloading InnoExtract...')
            with open(os.path.join(dest_path, archive), 'wb') as dl:
                util.download(link, dl)

            progress.finish_task()
            progress.update(0.13, 'Extracting InnoExtract...')

            util.extract_archive(archive, tempdir)
            shutil.move(os.path.join(tempdir, path), inno)

        # Make it executable
        mode = os.stat(inno).st_mode
        os.chmod(inno, mode | stat.S_IXUSR)

        progress.start_task(0.15, 0.75, 'Extracting FS2: %s')
        try:
            cmd = [inno, '-L', '-s', '-p', '-e', gog_path]
            logging.info('Running %s...', ' '.join(cmd))

            opts = dict()
            if sys.platform.startswith('win'):
                si = subprocess.STARTUPINFO()
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

                opts['startupinfo'] = si
                opts['stdin'] = subprocess.PIPE

            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=dest_path, **opts)

            if sys.platform.startswith('win'):
                p.stdin.close()

            buf = ''
            while p.poll() is None:
                while '\r' not in buf:
                    line = p.stdout.read(10)
                    if not line:
                        break
                    buf += line.decode('utf8', 'replace')

                buf = buf.split('\r')
                line = buf.pop(0)
                buf = '\r'.join(buf)

                if 'MiB/s' in line:
                    try:
                        if ']' in line:
                            line = line.split(']')[1]

                        line = line.strip().split('MiB/s')[0] + 'MiB/s'
                        percent = float(line.split('%')[0]) / 100

                        progress.update(percent, line)
                    except Exception:
                        logging.exception('Failed to process InnoExtract output!')
                else:
                    if line.strip() == 'not a supported Inno Setup installer':
                        self.post(-1)
                        return

                    logging.info('InnoExtract: %s', line)
        except Exception:
            logging.exception('InnoExtract failed!')
            return

        progress.finish_task()

        progress.update(0.95, 'Moving files...')
        self._makedirs(os.path.join(dest_path, 'data/players'))
        self._makedirs(os.path.join(dest_path, 'data/movies'))

        for item in glob.glob(os.path.join(dest_path, 'app', '*.vp')):
            shutil.move(item, os.path.join(dest_path, os.path.basename(item)))

        for item in glob.glob(os.path.join(dest_path, 'app/data/players', '*.hcf')):
            shutil.move(item, os.path.join(dest_path, 'data/players', os.path.basename(item)))

        for item in glob.glob(os.path.join(dest_path, 'app/data2', '*.mve')):
            shutil.move(item, os.path.join(dest_path, 'data/movies', os.path.basename(item)))

        for item in glob.glob(os.path.join(dest_path, 'app/data3', '*.mve')):
            shutil.move(item, os.path.join(dest_path, 'data/movies', os.path.basename(item)))

        progress.update(0.99, 'Cleanup...')
        os.unlink(inno)
        shutil.rmtree(os.path.join(dest_path, 'app'), ignore_errors=True)
        shutil.rmtree(os.path.join(dest_path, 'tmp'), ignore_errors=True)

        with open(os.path.join(dest_path, 'kn_tile.png'), 'wb') as stream:
            stream.write(read_file(':/html/images/mod-retail.png', decode=False))

        mod = repo.InstalledMod({
            'title': 'Retail FS2',
            'id': 'FS2',
            'version': '1.0',
            'type': 'tc',
            'folder': dest_path,
            'tile': 'kn_tile.png',
            'tile_path': os.path.join(dest_path, 'kn_tile.png')
        })
        mod.add_pkg(repo.InstalledPackage({
            'name': 'Content',
            'status': 'required',
            'folder': '.',
            'dependencies': [{
                'id': 'FSO',
                'version': '>=3.8.0-1'
            }]
        }))

        center.installed.add_mod(mod)
        mod.save()

        self.post(dest_path)

    def _makedirs(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)

    def finish(self):
        results = self.get_results()
        if len(results) < 1:
            QtWidgets.QMessageBox.critical(None, translate('tasks', 'Error'), self.tr(
                'The installer failed! Please read the log for more details...'))
            return
        elif results[0] == -1:
            QtWidgets.QMessageBox.critical(None, translate('tasks', 'Error'), self.tr(
                'The selected file wasn\'t a proper Inno Setup installer. Are you shure you selected the right file?'))
            return
        else:
            QtWidgets.QMessageBox.information(None, translate('tasks', 'Done'), self.tr(
                'FS2 has been successfully installed.'))

            center.main_win.update_mod_list()


class GOGCopyTask(progress.Task):
    can_abort = False

    def __init__(self, gog_path, dest_path):
        super(GOGCopyTask, self).__init__()

        self.done.connect(self.finish)
        self.add_work([(gog_path, dest_path)])
        self.title = 'Copying retail files...'

        if not center.installed.has('FSO'):
            try:
                fso = center.mods.query('FSO')
                run_task(InstallTask(fso.resolve_deps()))
            except repo.ModNotFound:
                logging.warn('Installing retail files but FSO is missing!')

    def work(self, paths):
        gog_path, dest_path = paths

        progress.update(0, 'Copying files...')
        self._makedirs(os.path.join(dest_path, 'data/players'))
        self._makedirs(os.path.join(dest_path, 'data/movies'))

        for item in glob.glob(os.path.join(gog_path, '*.vp')):
            shutil.copyfile(item, os.path.join(dest_path, os.path.basename(item)))

        for item in glob.glob(os.path.join(gog_path, 'data/players', '*.hcf')):
            shutil.copyfile(item, os.path.join(dest_path, 'data/players', os.path.basename(item)))

        for item in glob.glob(os.path.join(gog_path, 'data2', '*.mve')):
            shutil.copyfile(item, os.path.join(dest_path, 'data/movies', os.path.basename(item)))

        for item in glob.glob(os.path.join(gog_path, 'data3', '*.mve')):
            shutil.copyfile(item, os.path.join(dest_path, 'data/movies', os.path.basename(item)))

        with open(os.path.join(dest_path, 'kn_tile.png'), 'wb') as stream:
            stream.write(read_file(':/html/images/mod-retail.png', decode=False))

        mod = repo.InstalledMod({
            'title': 'Retail FS2',
            'id': 'FS2',
            'version': '1.0',
            'type': 'tc',
            'folder': dest_path,
            'tile': 'kn_tile.png',
            'tile_path': os.path.join(dest_path, 'kn_tile.png')
        })
        mod.add_pkg(repo.InstalledPackage({
            'name': 'Content',
            'status': 'required',
            'folder': '.',
            'dependencies': [{
                'id': 'FSO',
                'version': '>=3.8.0-RC3'
            }]
        }))

        center.installed.add_mod(mod)
        mod.save()

        self.post(dest_path)

    def _makedirs(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)

    def finish(self):
        center.main_win.update_mod_list()


class CheckUpdateTask(progress.Task):
    background = True

    def __init__(self):
        super(CheckUpdateTask, self).__init__()

        self.add_work(('',))
        self.title = 'Checking for updates...'

    def work(self, item):
        progress.update(0, 'Checking for updates...')

        update_base = util.pjoin(center.UPDATE_LINK, 'stable')
        version = util.get(update_base + '/version?me=' + center.VERSION)

        if version is None:
            logging.error('Update check failed!')
            return

        try:
            version = semantic_version.Version(version)
        except Exception:
            logging.exception('Failed to parse remote version!')
            return

        cur_version = semantic_version.Version(center.VERSION)
        if version > cur_version:
            center.signals.update_avail.emit(version)


class WindowsUpdateTask(progress.Task):

    def __init__(self):
        super(WindowsUpdateTask, self).__init__()

        self.done.connect(self.finish)
        self.add_work(('',))
        self.title = 'Installing update...'

    def work(self, item):
        # Download it.
        update_base = util.pjoin(center.UPDATE_LINK, 'stable')

        dir_name = tempfile.mkdtemp()
        updater = os.path.join(dir_name, 'knossos_updater.exe')

        progress.start_task(0, 0.98, 'Downloading update...')
        with open(updater, 'wb') as stream:
            util.download(update_base + '/updater.exe', stream)

        progress.finish_task()
        progress.update(0.99, 'Launching updater...')

        try:
            import win32api
            win32api.ShellExecute(0, 'open', updater, '/D=' + os.getcwd(), os.path.dirname(updater), 1)
        except Exception:
            logging.exception('Failed to launch updater!')
            self.post(False)
        else:
            self.post(True)
            center.app.quit()

    def finish(self):
        res = self.get_results()

        if len(res) < 1 or not res[0]:
            QtWidgets.QMessageBox.critical(None, 'Knossos', self.tr('Failed to launch the update!'))


class CopyFolderTask(progress.Task):

    def __init__(self, src_path, dest_path):
        super(CopyFolderTask, self).__init__()

        self.add_work(((src_path, dest_path),))
        self.title = 'Copying folder...'

    def work(self, p):
        src_path, dest_path = p

        if not os.path.isdir(src_path):
            logging.error('CopyFolderTask(): The src_path "%s" is not a folder!' % src_path)
            return

        progress.update(0, 'Scanning...')

        dest_base = os.path.dirname(dest_path)
        if not os.path.isdir(dest_base):
            os.makedirs(dest_base)

        files = []
        total_size = 0.0
        for src_prefix, dirs, files in os.walk(src_path):
            dest_prefix = os.path.join(dest_path, os.path.relpath(src_prefix, src_path))

            for sub in dirs:
                sdest = os.path.join(dest_prefix, sub)
                try:
                    os.mkdir(sdest)
                except OSError:
                    logging.exception('Failed to mkdir %s.' % sdest)

            for sub in files:
                sdest = os.path.join(dest_prefix, sub)
                ssrc = os.path.join(src_prefix, sub)
                files.append((ssrc, sdest))
                total_size += os.stat(ssrc).st_size

        bytes_done = 0
        for src, dest in files:
            progress.update(bytes_done / total_size, os.path.relpath(src, src_path))
            shutil.copyfile(src, dest)

            bytes_done += os.stat(src).st_size


def run_task(task, cb=None):
    def wrapper():
        cb(task.get_results())

    if cb is not None:
        task.done.connect(wrapper)

    center.signals.task_launched.emit(task)
    center.pmaster.add_task(task)
    return task
