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
import re
import hashlib
import semantic_version

from . import center, util, progress, nebula, repo, vplib
from .repo import Repo
from .qt import QtCore, QtWidgets, read_file


translate = QtCore.QCoreApplication.translate


class FetchTask(progress.Task):

    def __init__(self):
        super(FetchTask, self).__init__()
        self.title = 'Fetching mod list...'
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

    def finish(self):
        if not self.aborted:
            modlist = center.mods = Repo()
            res = self.get_results()
            res.sort(key=lambda x: x[0])

            for part in res:
                modlist.merge(part[1])

            modlist.save_json(os.path.join(center.settings_path, 'mods.json'))
            center.save_settings()
            center.main_win.update_mod_list()


class LoadLocalModsTask(progress.Task):
    can_abort = False
    _steps = 2

    def __init__(self):
        super(LoadLocalModsTask, self).__init__(threads=3)

        self.done.connect(self.finish)
        self.title = 'Loading installed mods...'

        if center.settings['base_path'] is None:
            logging.warning('A LoadLocalModsTask was launched even though no base path was set!')
        else:
            center.installed.clear()
            self.add_work((center.settings['base_path'],))
            self.add_work(center.settings['base_dirs'])

    def work(self, path):
        mods = center.installed

        subs = []
        mod_file = None

        try:
            for base in os.listdir(path):
                sub = os.path.join(path, base)

                if os.path.isdir(sub) and not sub.endswith('.dis'):
                    subs.append(sub)
                elif base.lower() == 'mod.json':
                    mod_file = sub
        except FileNotFoundError:
            logging.warning('The directory "%s" does not exist anymore!' % path)

        if mod_file:
            try:
                mod = repo.InstalledMod.load(mod_file)
                mods.add_mod(mod)
            except Exception:
                logging.exception('Failed to parse "%s"!', sub)

        self.add_work(subs)

    def finish(self):
        center.main_win.update_mod_list()


class CheckFilesTask(progress.MultistepTask):
    can_abort = False
    _mod = None
    _check_results = None
    _steps = 2

    def __init__(self, pkgs):
        super(CheckFilesTask, self).__init__()

        self.title = 'Checking %d packages...' % len(pkgs)
        self.pkgs = pkgs

        self.done.connect(self.finish)
        self._threads = 1

    def init1(self):
        pkgs = []

        for pkg in self.pkgs:
            mod = pkg.get_mod()
            pkgs.append((mod.folder, pkg))

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

                if util.check_hash(info['checksum'], mypath, False):
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
        fnames = set()
        modpaths = set()
        loose = []

        # Collect all filenames
        for pkg, s, c, m in self._check_results:
            modpath = pkg.get_mod().folder
            modpaths.add(modpath)

            # Ignore files are generated by Knossos. Only mod.json files that are in the location where we expect it to
            # be are ignored. All other mod.json files will be considered loose
            fnames.add(os.path.join(modpath, 'mod.json'))

            for info in pkg.filelist:
                # relative paths are valid here but we only want the filename
                fnames.add(os.path.normpath(os.path.join(modpath, info['filename'])))

        # Check for loose files.
        for modpath in modpaths:
            for path, dirs, files in os.walk(modpath):
                for item in files:
                    name = os.path.join(path, item)
                    if name not in fnames and not item.startswith(('__k_plibs', 'knossos.')):
                        loose.append(name)

        self._check_results.append((None, 0, 0, {'loose': loose}))
        self._results = self._check_results

    def finish(self):
        bad_packages = []
        for result in self._check_results:
            if result[0] is None:
                # This is the entry which contains the loose files
                continue

            if result[1] != result[2]:
                # If the number of checked files is different than the number of valid files then there is something
                # wrong with this package
                bad_packages.append(result[0])

        if len(bad_packages) > 0:
            msg = "An error was detected while validating the game file integrity. The following packages are invalid:"
            for pkg in bad_packages:
                msg += "\n  - Package %s of mod %s" % (pkg.name, pkg.get_mod().title)
            msg += "\n\nThese mods are invalid and need to be redownloaded before they can be played without errors."

            QtWidgets.QMessageBox.critical(None, 'Knossos', msg)



# TODO: Optimize, make sure all paths are relative (no mod should be able to install to C:\evil)
# TODO: Add error messages.
class InstallTask(progress.MultistepTask):
    _pkgs = None
    _pkg_names = None
    _mods = None
    _dls = None
    _copies = None
    _steps = 4
    _error = False
    _7z_lock = None
    check_after = True

    def __init__(self, pkgs, mod=None, check_after=True):
        super(InstallTask, self).__init__()

        self._mods = set()
        self._pkgs = []
        self._pkg_names = []
        self.check_after = check_after

        if sys.platform == 'win32':
            self._7z_lock = threading.Lock()

        if mod is not None:
            self.mods = [mod]

        for pkg in pkgs:
            try:
                pmod = center.installed.query(pkg.get_mod())
                if pmod.dev_mode:
                    # Don't modify mods which are in dev mode!
                    continue
            except repo.ModNotFound:
                pass

            ins_pkg = center.installed.add_pkg(pkg)
            pmod = ins_pkg.get_mod()
            self._pkgs.append(ins_pkg)
            self._mods.add(pmod)
            self._pkg_names.append((pmod.mid, ins_pkg.name))

            for item in ins_pkg.files.values():
                self._slot_prog[id(item)] = ('%s: %s' % (pmod.title, item['filename']), 0, 'Checking...')

        for m in self._mods:
            if m not in self.mods:
                self.mods.append(m)

        center.signals.repo_updated.emit()
        self.done.connect(self.finish)
        self.title = 'Installing mods...'

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
            else:
                QtWidgets.QMessageBox.critical(None, 'Knossos',
                    self.tr('The mod installation was aborted before it could finish. ' +
                        'You might have to uninstall the partially installed mod(s).'))
        elif self._error:
            msg = self.tr(
                'An error occured during the installation of a mod. It might be partially installed.\n' +
                'If you need more help, ask ngld or read the debug log!'
            )
            QtWidgets.QMessageBox.critical(None, 'Knossos', msg)

        if not isinstance(self, UpdateTask):
            run_task(LoadLocalModsTask())

    def init1(self):
        if center.settings['neb_user']:
            try:
                neb = nebula.NebulaClient()
                editable = neb.get_editable_mods()

                for mod in self._mods:
                    if mod.mid in editable:
                        mod.dev_mode = True
            except Exception:
                logging.exception('Failed to login to the Nebula')

        self._threads = 3
        self.add_work(self._mods)

    def work1(self, mod):
        modpath = mod.folder
        mfiles = mod.get_files()
        mnames = [f['filename'] for f in mfiles] + ['knossos.bmp', 'mod.json']
        self._local.slot = id(mod)
        self._slot_prog[id(mod)] = (mod.title, 0, '')

        archives = set()
        progress.start_task(0, 0.9, '%s')
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
                logging.error('Overwriting "%s" (%s) with version %s.' % (mod.mid, info['version'], mod.version))

        if os.path.isdir(modpath):
            # TODO: Figure out if we want to handle these files (i.e. remove them)
            for path, dirs, files in os.walk(modpath):
                relpath = path[len(modpath):].lstrip('/\\')
                for item in files:
                    itempath = util.pjoin(relpath, item)
                    if not itempath.startswith('kn_') and itempath not in mnames:
                        logging.info('File "%s" is left over.', itempath)
        else:
            logging.debug('Folder %s for %s does not yet exist.', mod, modpath)
            os.makedirs(modpath)

        amount = float(len(mfiles))
        inst_mods = center.installed.query_all(mod.mid)
        copies = []
        pkg_folders = {}

        # query_all is a generator so the exception will be thrown when looping over the result
        try:
            for mv in inst_mods:
                if mv.dev_mode:
                    pf = pkg_folders.setdefault(mv, {})

                    for pkg in mv.packages:
                        pf[pkg.name] = pkg.folder
        except repo.ModNotFound:
            inst_mods = []

        for i, info in enumerate(mfiles):
            if (mod.mid, info['package']) not in self._pkg_names:
                continue

            progress.update(i / amount, 'Checking %s: %s...' % (mod.title, info['filename']))

            # Check if we already have this file
            found = False
            for mv in inst_mods:
                if mv.dev_mode:
                    itempath = util.ipath(os.path.join(mv.folder, pkg_folders[mv][info['package']], info['filename']))
                else:
                    itempath = util.ipath(os.path.join(mv.folder, info['filename']))

                if os.path.isfile(itempath) and util.check_hash(info['checksum'], itempath):
                    copies.append((mod, info['package'], info['filename'], itempath))
                    found = True
                    break

            if not found:
                archives.add((mod.mid, info['package'], info['archive']))
                logging.debug('%s: %s is missing/broken for %s.', info['package'], info['filename'], mod)

        self.post((archives, copies))
        progress.finish_task()
        progress.start_task(0.9, 0, 'Downloading logos...')

        # Make sure the images are in the mod folder so that they won't be deleted during the next
        # FetchTask.
        for prop in ('logo', 'tile', 'banner'):
            img_path = getattr(mod, prop)
            if img_path:
                ext = os.path.splitext(img_path)[1]
                dest = os.path.join(mod.folder, 'kn_' + prop + ext)

                if '://' in img_path:
                    # That's a URL
                    with open(dest, 'wb') as fobj:
                        util.download(img_path, fobj)

                setattr(mod, prop, dest)

        for prop in ('screenshots', 'attachments'):
            im_paths = getattr(mod, prop)
            for i, path in enumerate(im_paths):
                ext = os.path.splitext(path)[1]
                dest = os.path.join(mod.folder, 'kn_' + prop + '_' + str(i) + ext)

                if '://' in path:
                    with open(dest, 'wb') as fobj:
                        util.download(path, fobj)

                im_paths[i] = dest

        progress.finish_task()
        progress.update(1, 'Done')

    def init2(self):
        archives = set()
        copies = []
        downloads = []

        for a, c in self.get_results():
            archives |= a
            copies.extend(c)

        self._copies = copies

        for pkg in self._pkgs:
            mod = pkg.get_mod()
            for oitem in pkg.files.values():
                if (mod.mid, pkg.name, oitem['filename']) in archives:
                    item = oitem.copy()
                    item['mod'] = mod
                    item['pkg'] = pkg
                    item['_id'] = id(oitem)
                    downloads.append(item)
                else:
                    del self._slot_prog[id(oitem)]

        if len(archives) == 0:
            logging.info('Nothing to do for this InstallTask!')
        elif len(downloads) == 0:
            logging.error('Somehow we didn\'t find any downloads for this InstallTask!')
            self._error = True

        self._threads = 0
        self.add_work(downloads)

    def work2(self, archive):
        self._local.slot = archive['_id']

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

            progress.update(0.98, 'Extracting...')
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

            dev_mode = archive['pkg'].get_mod().dev_mode

            for item in archive['pkg'].filelist:
                if item['archive'] != archive['filename']:
                    continue

                src_path = os.path.join(cpath, item['orig_name'])
                if dev_mode:
                    dest_path = util.ipath(os.path.join(modpath, archive['pkg'].folder, item['filename']))
                else:
                    dest_path = util.ipath(os.path.join(modpath, item['filename']))

                try:
                    dparent = os.path.dirname(dest_path)
                    if not os.path.isdir(dparent):
                        os.makedirs(dparent)

                    if dev_mode and archive['pkg'].is_vp:
                        progress.start_task(0.98, 0.02, '%s')
                        util.extract_vp_file(src_path, os.path.join(modpath, archive['pkg'].folder))

                        # Avoid confusing CheckTask with a missing VP file.
                        archive['pkg'].filelist = []
                    else:
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

            progress.update(1, 'Done.')

    def init3(self):
        self.add_work((None,))

    def work3(self, _):
        self._slot_prog['copies'] = ('Copy old files', 0, 'Waiting...')
        self._local.slot = 'copies'

        pkg_folders = {}

        count = float(len(self._copies))
        for i, info in enumerate(self._copies):
            mod, pkg_name, fn, src = info

            progress.update(i / count, fn)
            if mod.dev_mode:
                if mod not in pkg_folders:
                    pkg_folders[mod] = {}
                    for pkg in mod.packages:
                        pkg_folders[mod][pkg.name] = pkg.folder

                dest = os.path.join(mod.folder, pkg_folders[mod][pkg_name], fn)
            else:
                dest = os.path.join(mod.folder, fn)

            logging.debug('Copying %s to %s', src, dest)
            shutil.copy(src, dest)

        progress.update(1, 'Done')

    def init4(self):
        self.add_work((None,))

    def work4(self, _):
        # Generate mod.json files.
        for mod in self._mods:
            try:
                mod.save()
                util.get(center.settings['nebula_link'] + 'api/1/track/install/' + mod.mid)
            except Exception:
                logging.exception('Failed to generate mod.json file for %s!' % mod.mid)


# TODO: make sure all paths are relative (no mod should be able to install to C:\evil)
class UninstallTask(progress.MultistepTask):
    _pkgs = None
    _mods = None
    _steps = 2
    check_after = True

    def __init__(self, pkgs, mods=[]):
        super(UninstallTask, self).__init__()

        self._pkgs = []
        self._mods = []

        for pkg in pkgs:
            try:
                self._pkgs.append(center.installed.query(pkg))
            except repo.ModNotFound:
                logging.exception('Someone tried to uninstall a non-existant package (%s, %s)! Skipping it...', pkg.get_mod().mid, pkg.name)

        for mod in mods:
            try:
                self._mods.append(center.installed.query(mod))
            except repo.ModNotFound:
                logging.exception('Someone tried to uninstall a non-existant %s!', mod)

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

                my_files = [os.path.join(modpath, 'mod.json'), mod.logo, mod.tile, mod.banner]
                my_files += mod.screenshots + mod.attachments
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
            elif not os.path.isdir(modpath):
                logging.error('Mod %s still has packages but mod folder "%s" is gone!' % (mod, modpath))
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
        # Update the local mod list which will remove the uninstalled mod
        run_task(LoadLocalModsTask())


class UpdateTask(InstallTask):
    _old_mod = None
    __check_after = True

    def __init__(self, mod, check_after=True):
        self._old_mod = mod
        new_mod = center.mods.query(mod.mid)
        self.__check_after = check_after

        old_pkgs = [pkg.name for pkg in mod.packages]
        pkgs = []

        for pkg in new_mod.packages:
            if pkg.name in old_pkgs or pkg.status == 'required':
                pkgs.append(pkg)

        super(UpdateTask, self).__init__(pkgs, new_mod, check_after=False)

    def finish(self):
        super(UpdateTask, self).finish()

        if not self.aborted and not self._error:
            # The new version has been succesfully installed, remove the old version.

            if len(self._old_mod.get_dependents()) == 0:
                run_task(UninstallTask(self._old_mod.packages))
            else:
                logging.debug('Not uninstalling %s after update because it still has dependents.', self._old_mod)
                run_task(LoadLocalModsTask())


class UploadTask(progress.MultistepTask):
    can_abort = True
    _steps = 2
    _client = None
    _mod = None
    _dir = None
    _login_failed = False
    _duplicate = False
    _reason = None
    _msg = None
    _success = False
    _msg_table = {
        'invalid version': 'the version number specified for this release is invalid!',
        'outdated version': 'there is already a release with the same or newer version on the nebula.',
        'unsupported archive checksum': 'your client sent an invalid checksum. You probably need to update.',
        'archive missing': 'one of your archives failed to upload.'
    }
    _question = QtCore.Signal()
    _question_result = False
    _question_cond = None

    def __init__(self, mod):
        super(UploadTask, self).__init__()

        self.title = 'Uploading mod...'
        self.mods = [mod]
        self._mod = mod.copy()

        self._threads = 2
        self._slot_prog = {
            'total': ('Status', 0, 'Waiting...')
        }

        self.done.connect(self.finish)
        self._question.connect(self.show_question)
        self._question_cond = threading.Condition()

    def abort(self):
        self._local.slot = 'total'
        progress.update(1, 'Aborted')

        super(UploadTask, self).abort()

    def show_question(self):
        res = QtWidgets.QMessageBox.question(None, 'Knossos', 'This mod has already been uploaded. If you continue, ' +
            'your metadata changes will be uploaded but the files will not be updated. Continue?')

        self._question_result = res == QtWidgets.QMessageBox.Yes
        with self._question_cond:
            self._question_cond.notify()

    def init1(self):
        self._local.slot = 'total'

        try:
            progress.update(0, 'Performing sanity checks...')
            if self._mod.mtype in ('mod', 'tc'):
                try:
                    exes = self._mod.get_executables()
                except Exception:
                    exes = []

                if len(exes) == 0:
                    self._reason = 'no exes'
                    self.abort()
                    return

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
            try:
                client.preflight_release(self._mod)
            except nebula.RequestFailedException as exc:
                if exc.args[0] == 'duplicated version':
                    with self._question_cond:
                        self._question.emit()
                        self._question_cond.wait()

                        if not self._question_result:
                            self._reason = 'aborted'
                            self.abort()
                            return

                    self._duplicate = True
                else:
                    raise

            if not self._duplicate:
                progress.update(0.15, 'Scanning files...')
                archives = []
                fnames = {}
                conflicts = {}
                for pkg in self._mod.packages:
                    ar_name = pkg.name + '.7z'
                    pkg_path = os.path.join(self._mod.folder, pkg.folder)
                    pkg.filelist = []

                    for sub, dirs, files in os.walk(pkg_path):
                        relsub = os.path.relpath(sub, pkg_path)
                        for fn in files:
                            relpath = os.path.join(relsub, fn).replace('\\', '/')

                            pkg.filelist.append({
                                'filename': relpath,
                                'archive': ar_name,
                                'orig_name': relpath,
                                'checksum': None
                            })

                            if not pkg.is_vp:
                                # VP conflicts don't cause problems and are most likely intentional
                                # which is why we ignore them.

                                if relpath in fnames:
                                    l = conflicts.setdefault(relpath, [fnames[relpath].name])
                                    l.append(pkg.name)

                                fnames[relpath] = pkg

                    if len(pkg.filelist) == 0:
                        self._reason = 'empty pkg'
                        self._msg = pkg.name
                        self.abort()
                        return

                    archives.append(pkg)
                    self._slot_prog[pkg.name] = (pkg.name + '.7z', 0, 'Waiting...')

                if conflicts:
                    msg = ''
                    for name in sorted(conflicts.keys()):
                        msg += '\n%s is in %s' % (name, util.human_list(conflicts[name]))

                    self._reason = 'conflict'
                    self._msg = msg
                    self.abort()
                    return

                self._slot_prog['#checksums'] = ('Checksums', 0, '')
                self._local.slot = '#checksums'

                fc = float(sum([len(pkg.filelist) for pkg in self._mod.packages]))
                done = 0
                for pkg in self._mod.packages:
                    pkg_path = os.path.join(self._mod.folder, pkg.folder)

                    for fn in pkg.filelist:
                        progress.update(done / fc, fn['filename'])
                        fn['checksum'] = util.gen_hash(os.path.join(pkg_path, fn['filename']))
                        done += 1

                progress.update(1, 'Done')
                self._local.slot = 'total'

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
        except Exception:
            logging.exception('Error during upload initalisation!')
            self._reason = 'unknown'
            self.abort()

    def work1(self, pkg):
        self._local.slot = pkg.name

        ar_name = pkg.name + '.7z'
        ar_path = os.path.join(self._dir.name, ar_name)

        try:
            progress.update(0, 'Comparing...')

            hasher = hashlib.new('sha512')
            for item in sorted(pkg.filelist, key=lambda a: a['filename']):
                line = '%s#%s\n' % (item['filename'], item['checksum'])
                hasher.update(line.encode('utf8'))

            content_ck = hasher.hexdigest()
            result, meta = self._client.is_uploaded(content_checksum=content_ck)
            if result:
                # The file is already uploaded
                pkg.files[ar_name] = {
                    'filename': ar_name,
                    'dest': '',
                    'checksum': ('sha256', meta['checksum']),
                    'filesize': meta['filesize']
                }

                progress.update(1, 'Done!')
                return

            progress.update(0, 'Packing...')
            if pkg.is_vp:
                vp_name = pkg.name + '.vp'
                vp_path = os.path.join(self._dir.name, vp_name)
                vp = vplib.VpWriter(vp_path)
                pkg_path = os.path.join(self._mod.folder, pkg.folder)

                for sub, dirs, files in os.walk(pkg_path):
                    relsub = os.path.relpath(sub, pkg_path)
                    for fn in files:
                        relpath = os.path.join(relsub, fn)
                        vp.add_file(relpath, os.path.join(sub, fn))

                progress.start_task(0.0, 0.1, '%s')
                vp.write()

                progress.update(1, 'Calculating checksum...')
                progress.finish_task()

                pkg.filelist = [{
                    'filename': vp_name,
                    'archive': ar_name,
                    'orig_name': vp_name,
                    'checksum': util.gen_hash(vp_path)
                }]

                progress.start_task(0.1, 0.3, '%s')
            else:
                progress.start_task(0.0, 0.4, '%s')

            if pkg.is_vp:
                p = util.Popen([util.SEVEN_PATH, 'a', '-bsp1', ar_path, vp_name],
                    cwd=self._dir.name, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            else:
                p = util.Popen([util.SEVEN_PATH, 'a', '-bsp1', ar_path, '.'],
                    cwd=os.path.join(self._mod.folder, pkg.folder), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            line_re = re.compile(r'^\s*([0-9]+)%')
            buf = ''
            while p.poll() is None:
                while '\b' not in buf:
                    line = p.stdout.read(10)
                    if not line:
                        break
                    buf += line.decode('utf8', 'replace')

                buf = buf.split('\b')
                line = buf.pop(0)
                buf = '\b'.join(buf)

                m = line_re.match(line)
                if m:
                    progress.update(int(m.group(1)) / 100., 'Compressing...')

            if p.returncode != 0:
                logging.error('Failed to build %s!' % ar_name)
                self.abort()
                return

            progress.finish_task()
            progress.start_task(0.4, 0.6, '%s')
            progress.update(0, 'Preparing upload...')

            pkg.files[ar_name] = {
                'filename': ar_name,
                'dest': '',
                'checksum': util.gen_hash(ar_path),
                'filesize': os.stat(ar_path).st_size
            }

            retries = 3
            while retries > 0:
                retries -= 1
                try:
                    self._client.upload_file(ar_name, ar_path, content_checksum=content_ck)
                    break
                except nebula.RequestFailedException:
                    logging.exception('Failed upload, retrying...')

            progress.finish_task()
            progress.update(1, 'Done!')
        except nebula.RequestFailedException:
            logging.exception('Failed request to nebula during upload!')

            self._reason = 'archive missing'
            self.abort()
        except Exception:
            logging.exception('Unknown error during package packing!')

            self._reason = 'unknown'
            self.abort()

    def init2(self):
        self._local.slot = 'total'

        try:
            progress.update(0.8, 'Finishing...')

            if self._duplicate:
                self._client.update_release(self._mod)
            else:
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
        try:
            if self._dir:
                util.retry_helper(self._dir.cleanup)
        except OSError:
            # This is not a critical error so we only log it for now
            logging.exception('Failed to remove temporary folder after upload!')

        if self._login_failed:
            message = 'Failed to login!'
        elif self._reason == 'unauthorized':
            message = 'You are not authorized to edit this mod!'
        elif self._success:
            message = 'Successfully uploaded mod!'
        elif self._reason in self._msg_table:
            message = "Your mod couldn't be uploaded because %s" % self._msg_table[self._reason]
        elif self._reason == 'conflict':
            message = "I can't upload this mod because at least one file is contained in multiple packages.\n"
            message += self._msg
        elif self._reason == 'empty pkg':
            message = 'The package %s is empty!' % self._msg
        elif self._reason == 'no exes':
            message = 'The mod has no executables selected!'
        elif self._reason == 'aborted':
            return
        else:
            message = 'An unexpected error occured! Sorry...'

        center.main_win.browser_ctrl.bridge.taskMessage.emit(message)


class GOGExtractTask(progress.Task):
    can_abort = False

    def __init__(self, gog_path, dest_path):
        super(GOGExtractTask, self).__init__()

        self.done.connect(self.finish)
        self.add_work([(gog_path, dest_path)])
        self.title = 'Installing FS2 from GOG...'

        self._makedirs(dest_path)
        create_retail_mod(dest_path)
        center.main_win.update_mod_buttons('home')

        self.mods = [center.installed.query('FS2')]
        self._slot_prog['total'] = ('Status', 0, 'Waiting...')

        if not center.installed.has('FSO'):
            try:
                fso = center.mods.query('FSO')
                run_task(InstallTask(fso.resolve_deps()))
            except repo.ModNotFound:
                logging.warning('Installing retail files but FSO is missing!')

    def work(self, paths):
        gog_path, dest_path = paths
        self._local.slot = 'total'

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
            center.main_win.update_mod_list()
            center.main_win.browser_ctrl.bridge.retailInstalled.emit()


class GOGCopyTask(progress.Task):
    can_abort = False

    def __init__(self, gog_path, dest_path):
        super(GOGCopyTask, self).__init__()

        self.done.connect(self.finish)
        self.add_work([(gog_path, dest_path)])
        self.title = 'Copying retail files...'

        self._makedirs(dest_path)
        create_retail_mod(dest_path)
        center.main_win.update_mod_buttons('home')

        self.mods = [center.installed.query('FS2')]
        self._slot_prog['total'] = ('Status', 0, 'Waiting...')

        if not center.installed.has('FSO'):
            try:
                fso = center.mods.query('FSO')
                run_task(InstallTask(fso.resolve_deps()))
            except repo.ModNotFound:
                logging.warning('Installing retail files but FSO is missing!')

    def work(self, paths):
        gog_path, dest_path = paths
        self._local.slot = 'total'

        progress.update(0, 'Creating directories...')
        self._makedirs(os.path.join(dest_path, 'data/players'))
        self._makedirs(os.path.join(dest_path, 'data/movies'))

        progress.update(1 / 4., 'Copying VPs...')
        for item in glob.glob(os.path.join(gog_path, '*.vp')):
            shutil.copyfile(item, os.path.join(dest_path, os.path.basename(item)))

        progress.update(2 / 4., 'Copying player profiles...')
        for item in glob.glob(os.path.join(gog_path, 'data/players', '*.hcf')):
            shutil.copyfile(item, os.path.join(dest_path, 'data/players', os.path.basename(item)))

        progress.update(3 / 4., 'Copying cutscenes...')
        for item in glob.glob(os.path.join(gog_path, 'data2', '*.mve')):
            shutil.copyfile(item, os.path.join(dest_path, 'data/movies', os.path.basename(item)))

        for item in glob.glob(os.path.join(gog_path, 'data3', '*.mve')):
            shutil.copyfile(item, os.path.join(dest_path, 'data/movies', os.path.basename(item)))

        progress.update(1, 'Done')
        self.post(dest_path)

    def _makedirs(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)

    def finish(self):
        center.main_win.update_mod_list()
        center.main_win.browser_ctrl.bridge.retailInstalled.emit()


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

        plan = []
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
                plan.append((ssrc, sdest))
                total_size += os.stat(ssrc).st_size

        bytes_done = 0
        for src, dest in plan:
            progress.update(bytes_done / total_size, os.path.relpath(src, src_path))
            shutil.copyfile(src, dest)

            bytes_done += os.stat(src).st_size


class VpExtractionTask(progress.Task):
    def __init__(self, installed_mod, ini_mod):
        super(VpExtractionTask, self).__init__()

        self.mod = installed_mod
        self.ini_mod = ini_mod

        self.title = 'Extracting VP files...'

        self._threads = 1  # VP extraction does not benefit from multiple threads

        for vp_file in os.listdir(ini_mod.folder):
            # We only look at vp files
            if not vp_file.lower().endswith(".vp"):
                continue

            vp_path = os.path.join(ini_mod.folder, vp_file)

            self.add_work((vp_path,))

    def work(self, vp_file):
        base_filename = os.path.basename(vp_file).replace(".vp", "")

        dest_folder = os.path.join(self.mod.folder, base_filename)

        progress.start_task(0.0, 1.0, 'Extracting %s')

        util.extract_vp_file(vp_file, dest_folder)

        progress.finish_task()
        # Collect the extracted vp files so we can use that once extraction has finished
        self.post(vp_file)


def run_task(task, cb=None):
    def wrapper():
        cb(task.get_results())

    if cb is not None:
        task.done.connect(wrapper)

    center.signals.task_launched.emit(task)
    center.pmaster.add_task(task)
    return task


def create_retail_mod(dest_path):
    # Remember to run tools/common/update_file_list.py if you add new files!
    files = {
        'tile': ':/html/images/retail_data/mod-retail.png',
        'banner': ':/html/images/retail_data/banner-retail.png',
    }

    screenshots = [':/html/images/retail_data/screen01.jpg', ':/html/images/retail_data/screen02.jpg', ':/html/images/retail_data/screen03.jpg', ':/html/images/retail_data/screen04.jpg', ':/html/images/retail_data/screen05.jpg', ':/html/images/retail_data/screen06.jpg', ':/html/images/retail_data/screen07.jpg', ':/html/images/retail_data/screen08.jpg', ':/html/images/retail_data/screen09.jpg', ':/html/images/retail_data/screen10.jpg', ':/html/images/retail_data/screen11.jpg', ':/html/images/retail_data/screen12.jpg']

    mod = repo.InstalledMod({
        'title': 'Retail FS2',
        'id': 'FS2',
        'version': '1.20',
        'type': 'tc',
        'description':
'[b][i]The year is 2367, thirty two years after the Great War. Or at least that is what YOU thought was the Great War. ' +
'The endless line of Shivan capital ships, bombers and fighters with super advanced technology was nearly overwhelming.\n\n' +
'As the Terran and Vasudan races finish rebuilding their decimated societies, a disturbance lurks in the not-so-far ' +
'reaches of the Gamma Draconis system.\n\nYour nemeses have arrived... and they are wondering what happened to ' +
'their scouting party.[/i][/b]\n\n[hr]FreeSpace 2 is a 1999 space combat simulation computer game developed by Volition as ' +
'the sequel to Descent: FreeSpace – The Great War. It was completed ahead of schedule in less than a year, and ' +
'released to very positive reviews.\n\nThe game continues on the story from Descent: FreeSpace, once again ' +
'thrusting the player into the role of a pilot fighting against the mysterious aliens, the Shivans. While defending ' +
'the human race and its alien Vasudan allies, the player also gets involved in putting down a rebellion. The game ' +
'features large numbers of fighters alongside gigantic capital ships in a battlefield fraught with beams, shells and ' +
'missiles in detailed star systems and nebulae.',
        'release_thread': 'http://www.hard-light.net/forums/index.php',
        'videos': ['https://www.youtube.com/watch?v=ufViyhrXzTE'],
        'first_release': '1999-09-30',
        'last_update': '1999-12-03',
        'folder': dest_path
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

    for prop, path in files.items():
        ext = os.path.splitext(path)[1]
        im_path = os.path.join(dest_path, 'kn_' + prop + ext)
        with open(im_path, 'wb') as stream:
            stream.write(read_file(path, decode=False))

        setattr(mod, prop, im_path)

    for i, path in enumerate(screenshots):
        ext = os.path.splitext(path)[1]
        im_path = os.path.join(dest_path, 'kn_screen_' + str(i) + ext)
        with open(im_path, 'wb') as stream:
            stream.write(read_file(path, decode=False))

        mod.screenshots.append(im_path)

    center.installed.add_mod(mod)
    mod.save()

    return mod
