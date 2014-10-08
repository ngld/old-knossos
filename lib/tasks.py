## Copyright 2014 fs2mod-py authors, see NOTICE file
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
import subprocess
import shutil
import glob
import stat
import json
import tempfile

import manager
from lib import util, progress, repo
from lib.repo import Repo, InstalledRepo
from lib.qt import QtGui


class FetchTask(progress.Task):

    def __init__(self):
        super(FetchTask, self).__init__()
        progress.update(0, 'Fetching mod list...')

        # Remove all logos.
        for path in glob.glob(os.path.join(manager.settings_path, 'logo*.*')):
            if os.path.isfile(path):
                logging.info('Removing old logo "%s"...', path)
                os.unlink(path)
        
        self.done.connect(self.finish)

        if repo.CPU_INFO is None:
            self.add_work(['init'])
        else:
            self.add_work([(i * 100, link[0]) for i, link in enumerate(manager.settings['repos'])])
    
    def work(self, params):
        if params == 'init':
            progress.update(0, 'Checking CPU...')

            # We're doing this here because we don't want to block the UI.
            repo.CPU_INFO = util.get_cpuinfo()

            self.add_work([(i * 100, link[0]) for i, link in enumerate(manager.settings['repos'])])
            return

        prio, link = params
        
        progress.update(0.1, 'Fetching "%s"...' % link)

        try:
            raw_data = util.get(link).read().decode('utf8', 'replace')

            data = Repo()
            data.is_link = True
            data.base = os.path.dirname(link)
            data.parse(raw_data)
        except:
            logging.exception('Failed to decode "%s"!', link)
            return
        
        progress.update(0.5, 'Loading logos...')
        data.save_logos(manager.settings_path)
        
        self.post((prio, data))
    
    def finish(self):
        if not self.aborted:
            modlist = manager.settings['mods'] = Repo()
            res = self.get_results()
            res.sort(key=lambda x: x[0])
            
            for part in res:
                modlist.merge(part[1])
            
            filelist = manager.settings['known_files'] = {}
            for mod in modlist.get_list():
                for pkg in mod.packages:
                    for name, ar in pkg.files.items():
                        path = util.pjoin(mod.folder, ar['dest'])
                        if ar['is_archive']:
                            for item in ar['contents']:
                                filelist[util.pjoin(path, item)] = (mod.mid, pkg.name)
                        else:
                            filelist[util.pjoin(path, name)] = (mod.mid, pkg.name)

            manager.save_settings()
        
        manager.run_task(CheckTask())


class CheckTask(progress.Task):
    can_abort = False
    
    def __init__(self, mods=None):
        super(CheckTask, self).__init__(threads=3)
        
        if mods is None:
            mods = manager.settings['mods'].get_list()

        pkgs = []
        for mod in mods:
            pkgs.extend(mod.packages)

        self.done.connect(self.finish)
        self.add_work(pkgs)
        progress.update(0, 'Checking installed mods...')

    def work(self, pkg):
        fs2path = manager.settings['fs2_path']
        modpath = os.path.join(fs2path, pkg.get_mod().folder)
        files = [item for item in pkg.get_mod().filelist.values() if item['package'] == pkg.name]
        
        count = float(len(files))
        success = 0
        checked = 0
        
        archives = set()
        msgs = []
        
        for info in files:
            mypath = util.ipath(os.path.join(modpath, info['filename']))
            fix = False
            if os.path.isfile(mypath):
                progress.update(checked / count, 'Checking "%s"...' % (info['filename']))
                
                if util.gen_hash(mypath) == info['md5sum']:
                    success += 1
                else:
                    msgs.append('File "%s" is corrupted. (checksum mismatch)' % (info['filename']))
                    fix = True
            else:
                msgs.append('File "%s" is missing.' % (info['filename']))
                fix = True
            
            if fix:
                archives.add(info['archive'])
            
            checked += 1
        
        if pkg.get_mod().folder != '':
            prefix = len(manager.settings['fs2_path'])
            filelist = manager.settings['known_files']
            lines = []
            for sub_path, dirs, files in os.walk(modpath):
                for name in files:
                    my_path = os.path.join(sub_path[prefix:], name).replace('\\', '/').lower().lstrip('/')
                    lines.append('  * %s' % my_path)
            
            if len(lines) > 0:
                msgs.append('User-added files:\n' + '\n'.join(lines))
        
        self.post((pkg, archives, success, checked, msgs))

    def finish(self):
        results = self.get_results()

        installed = manager.installed = InstalledRepo()
        mods = set()

        if manager.settings['installed_mods'] is not None:
            installed.set(manager.settings['installed_mods'])
        
        for pkg, archives, s, c, m in results:
            mod = pkg.get_mod()
            mods.add(mod)
            #my_shared = shared_set & set([util.pjoin(mod.folder, item) for item in pkg.get_files().keys()])
            pinfo = installed.query(mod.mid, pkg.name)
            
            if s == c:
                # Installed
                if pinfo is None:
                    pinfo = installed.add_pkg(pkg)

                pinfo.state = 'installed'
                
            elif s == 0:  # or s == len(my_shared):
                # Not Installed
                if pinfo is not None:
                    # What?!
                    logging.warning('Package %s of mod %s (%s) is not installed but in the local repo.' % (pkg.name, mod.mid, mod.title))
                    pinfo.state = 'not installed'

            elif pinfo is None:
                # Assume it's not installed.
                logging.info('Found some weird files from package %s of mod %s (%s) but it\'s not installed.' % (pkg.name, mod.mid, mod.title))

            else:
                if pinfo.version < pkg.version:
                    # There's an update available!
                    pinfo.state = 'has_update'
                else:
                    # It's corrupted.
                    pinfo.state = 'corrupted'

            if pinfo is not None:
                pinfo.check_notes = m
                pinfo.files_ok = s
                pinfo.files_checked = c
                pinfo.files_shared = 0  # len(my_shared)

        for mod in mods:
            if mod.mid in installed.mods:
                im = installed.mods[mod.mid]
                im.logo = mod.logo

        manager.settings['installed_mods'] = installed.get()
        manager.save_settings()
        manager.signals.repo_updated.emit()


# TODO: Optimize, make sure all paths are relative (no mod should be able to install to C:\evil)
class InstallTask(progress.MultistepTask):
    _pkgs = None
    _steps = 3

    def __init__(self, pkgs):
        self._pkgs = pkgs
        super(InstallTask, self).__init__()

        progress.update(0, 'Installing mods...')

    def abort(self):
        super(InstallTask, self).abort()

        util.cancel_downloads()

    def init1(self):
        mods = set()
        for pkg in self._pkgs:
            mods.add(pkg.get_mod())

        self.add_work(mods)

    def work1(self, mod):
        fs2_path = manager.settings['fs2_path']
        modpath = os.path.join(fs2_path, mod.folder)
        mfiles = mod.filelist

        archives = set()
        progress.update(0, 'Checking %s...' % mod.title)
        
        if mod.folder != '':
            for path, dirs, files in os.walk(modpath):
                relpath = path[len(modpath):].lstrip('/')
                for item in files:
                    itempath = util.pjoin(relpath, item)
                    if itempath not in mfiles:
                        logging.info('File "%s" is left over.', itempath)

        for item, info in mfiles.items():
            itempath = util.ipath(os.path.join(modpath, item))
            if not os.path.isfile(itempath) or util.gen_hash(itempath) != info['md5sum']:
                archives.add((mod.mid, info['package'], info['archive']))

        self.post(archives)

    def init2(self):
        archives = set()

        for a in self.get_results():
            archives |= a

        self.add_work([(pkg, archives) for pkg in self._pkgs])

    def work2(self, p):
        pkg, archives = p
        mid = pkg.get_mod().mid
        fs2path = manager.settings['fs2_path']
        modpath = os.path.join(fs2path, pkg.get_mod().folder)
        files = []

        for f_mid, pkg_name, fname in archives:
            if f_mid == mid and pkg.name == pkg_name:  # and fname in pkg.files:
                files.append(fname)

        count = float(len(files))
        for i, fname in enumerate(files):
            info = pkg.files[fname]
            dest = os.path.join(modpath, info['dest'])

            progress.start_task(i / count, 1 / count)

            with tempfile.TemporaryDirectory() as tpath:
                arpath = os.path.join(tpath, fname)

                with open(arpath, 'wb') as fobj:
                    util.try_download(info['urls'], fobj)

                if self.aborted:
                    return

                if info['is_archive']:
                    progress.update(1, 'Extracting %s...' % fname)

                    cpath = os.path.join(tpath, 'content')
                    os.mkdir(cpath)
                    util.extract_archive(arpath, cpath)

                    for sub_path, dirs, files in os.walk(cpath):
                        destpath = util.ipath(os.path.join(dest, sub_path[len(cpath):].lstrip('/')))

                        if not os.path.isdir(destpath):
                            logging.debug('Creating path "%s"...', destpath)
                            os.makedirs(destpath)

                        for item in files:
                            spath = os.path.join(sub_path, item)
                            dpath = util.ipath(os.path.join(destpath, item))

                            logging.debug('Moving "%s" to "%s"...', spath, dpath)
                            if os.path.isfile(dpath):
                                os.unlink(dpath)
                            elif os.path.isdir(dpath):
                                logging.warning('What?! "%s" is a directory! (I was expecting a file!)', dpath)
                                shutil.rmtree(dpath)

                            shutil.move(spath, dpath)
                else:
                    dpath = util.ipath(os.path.join(dest, fname))
                    if os.path.isfile(dpath):
                        os.unlink(dpath)
                    elif os.path.isdir(dpath):
                        logging.warning('What?! "%s" is a directory! (I was expecting a file!)', dpath)
                        shutil.rmtree(dpath)

                    shutil.move(arpath, dpath)

            progress.finish_task()

    def init3(self):
        mods = set()

        # Register installed pkgs
        for pkg in self._pkgs:
            manager.installed.add_pkg(pkg)
            mods.add(pkg.get_mod())

        manager.settings['installed_mods'] = manager.installed.get()

        self.done.connect(self.finish)
        self.add_work(mods)

    def work3(self, mod):
        fs2path = manager.settings['fs2_path']
        progress.update(0, 'Installing %s...' % (mod.title))

        for act in mod.actions:
            path_prefix = os.path.join(fs2path, mod.folder)
            if act.get('glob', True):
                path_prefix = glob.escape(path_prefix)

            try:
                paths = []
                for item in act['paths']:
                    if act.get('glob', True):
                        paths.extend(glob.iglob(os.path.join(path_prefix, item.lstrip('/'))))
                    else:
                        paths.append(os.path.join(path_prefix, item.lstrip('/')))

                if act['type'] == 'delete':
                    for item in paths:
                        logging.debug('Removing "%s"...', item)
                        shutil.rmtree(item)
                elif act['type'] == 'move':
                    dest = os.path.join(fs2path, mod.folder, act['dest'].lstrip('/'))
                    for item in paths:
                        logging.debug('Moving "%s" to "%s"...', item, dest)
                        shutil.move(item, dest)
                elif act['type'] == 'copy':
                    dest = os.path.join(fs2path, mod.folder, act['dest'].lstrip('/'))
                    for item in paths:
                        logging.debug('Copying "%s" to "%s"...', item, dest)
                        shutil.copytree(item, dest)
                elif act['type'] == 'mkdir':
                    for item in paths:
                        os.makedirs(item)
                else:
                    logging.error('Unknown mod action "%s" in mod "%s" (%s)!', act['type'], mod.title, mod.mid)
            except OSError:
                logging.exception('A path action failedmsg')

    def finish(self):
        manager.signals.repo_updated.emit()


# TODO: make sure all paths are relative (no mod should be able to install to C:\evil)
class UninstallTask(progress.Task):
    _pkgs = None

    def __init__(self, pkgs):
        super(UninstallTask, self).__init__()

        self._pkgs = pkgs

        self.done.connect(self.finish)
        self.add_work(pkgs)
        progress.update(0, 'Uninstalling mods...')

    def work(self, pkg):
        fs2path = manager.settings['fs2_path']
        mod = pkg.get_mod()

        for item in pkg.get_files():
            path = util.ipath(os.path.join(fs2path, mod.folder, item))
            if not os.path.isfile(path):
                logging.warning('File "%s" for mod "%s" (%s) is missing during uninstall!', item, mod.title, mod.mid)
            else:
                os.unlink(path)

        # TODO: Remove empty directories.

    def finish(self):
        # Unregister uninstalled pkgs.
        for pkg in self._pkgs:
            manager.installed.del_pkg(pkg)

        manager.settings['installed_mods'] = manager.installed.get()
        manager.signals.repo_updated.emit()


class GOGExtractTask(progress.Task):
    can_abort = False
    
    def __init__(self, gog_path, dest_path):
        super(GOGExtractTask, self).__init__()
        
        self.done.connect(self.finish)
        self.add_work([(gog_path, dest_path)])
        progress.update(0, 'Installing FS2 from GOG...')
    
    def work(self, paths):
        gog_path, dest_path = paths
        
        progress.start_task(0, 0.03, 'Looking for InnoExtract...')
        data = util.get(manager.settings['innoextract_link']).read().decode('utf8', 'replace')
        progress.finish_task()
        
        try:
            data = json.loads(data)
        except:
            logging.exception('Failed to read JSON data!')
            return
        
        link = None
        path = None
        for plat, info in data.items():
            if sys.platform.startswith(plat):
                link, path = info
                break
        
        if link is None:
            logging.error('Couldn\'t find an innoextract download for "%s"!', sys.platform)
            return
        
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
                    except:
                        logging.exception('Failed to process InnoExtract output!')
                else:
                    if line.strip() == 'not a supported Inno Setup installer':
                        self.post(-1)
                        return
                    
                    logging.info('InnoExtract: %s', line)
        except:
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
        
        # TODO: Test & improve
        self.post(dest_path)
    
    def _makedirs(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)
    
    def finish(self):
        results = self.get_results()
        if len(results) < 1:
            QtGui.QMessageBox.critical(manager.main_win.win, 'Error', 'The installer failed! Please read the log for more details...')
            return
        elif results[0] == -1:
            QtGui.QMessageBox.critical(manager.main_win.win, 'Error', 'The selected file wasn\'t a proper Inno Setup installer. Are you shure you selected the right file?')
            return
        else:
            QtGui.QMessageBox.information(manager.main_win.win, 'Done', 'FS2 was successfully installed.')

        fs2_path = results[0]
        manager.settings['fs2_path'] = fs2_path
        manager.settings['fs2_bin'] = None
        
        for item in glob.glob(os.path.join(fs2_path, 'fs2_*.exe')):
            if os.path.isfile(item):
                manager.settings['fs2_bin'] = os.path.basename(item)
                break
        
        manager.save_settings()
        manager.main_win.check_fso()
