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
import subprocess
import shutil
import glob
import stat
import json
import tempfile
import semantic_version

from . import center, util, progress, repo, api
from .repo import Repo
from .qt import QtGui


class FetchTask(progress.Task):

    def __init__(self):
        super(FetchTask, self).__init__()
        progress.update(0, 'Fetching mod list...')

        # Remove all logos.
        for path in glob.glob(os.path.join(center.settings_path, 'logo*.*')):
            if os.path.isfile(path):
                logging.info('Removing old logo "%s"...', path)
                os.unlink(path)
        
        self.done.connect(self.finish)

        if repo.CPU_INFO is None:
            self.add_work(['init'])
        else:
            self.add_work([(i * 100, link[0]) for i, link in enumerate(center.settings['repos'])])
    
    def work(self, params):
        if params == 'init':
            progress.update(0, 'Checking CPU...')

            # We're doing this here because we don't want to block the UI.
            repo.CPU_INFO = util.get_cpuinfo()

            self.add_work([(i * 100, link[0]) for i, link in enumerate(center.settings['repos'])])
            return

        prio, link = params
        
        progress.update(0.1, 'Fetching "%s"...' % link)

        try:
            raw_data = util.get(link)

            data = Repo()
            data.is_link = True
            data.base = os.path.dirname(link)
            data.parse(raw_data)
        except:
            logging.exception('Failed to decode "%s"!', link)
            return
        
        progress.update(0.5, 'Loading logos...')
        data.save_logos(center.settings_path)
        
        self.post((prio, data))
    
    def finish(self):
        if not self.aborted:
            modlist = center.settings['mods'] = Repo()
            res = self.get_results()
            res.sort(key=lambda x: x[0])
            
            for part in res:
                modlist.merge(part[1])
            
            filelist = center.settings['known_files'] = {}
            for mod in modlist.get_list():
                for pkg in mod.packages:
                    for name, ar in pkg.files.items():
                        path = util.pjoin(mod.folder, ar['dest'])
                        if ar['is_archive']:
                            for item in ar['contents']:
                                filelist[util.pjoin(path, item)] = (mod.mid, pkg.name)
                        else:
                            filelist[util.pjoin(path, name)] = (mod.mid, pkg.name)

            api.save_settings()
        
        run_task(CheckTask())


# TODO: Discover mods which don't have mod.json files.
class CheckTask(progress.MultistepTask):
    can_abort = False
    _steps = 2
    
    def __init__(self):
        super(CheckTask, self).__init__(threads=3)
        
        self.done.connect(self.finish)
        progress.update(0, 'Checking installed mods...')

    def init1(self):
        center.installed.clear()
        self.add_work(('',))

    def work1(self, p):
        fs2path = center.settings['fs2_path']
        mods = center.installed

        for subdir in os.listdir(fs2path):
            kfile = os.path.join(fs2path, subdir, 'mod.json')
            if os.path.isfile(kfile):
                try:
                    with open(kfile, 'r') as stream:
                        data = json.load(stream)
                        mod = repo.InstalledMod(data)
                        mod.folder = subdir
                        if mod.logo is not None:
                            mod.logo_path = os.path.join(fs2path, subdir, mod.logo)

                        mods.add_mod(mod)
                except:
                    logging.exception('Failed to parse "%s"!', kfile)
                    continue
                
                if mod.folder not in ('', '.'):
                    fs2path = center.settings['fs2_path']
                    modpath = os.path.join(fs2path, mod.folder)
                    filenames = [util.pjoin(mod.folder, f['filename']).lower() for f in mod.get_files()]
                    prefix = len(fs2path)
                    lines = []
                    
                    for sub_path, dirs, files in os.walk(modpath):
                        for name in files:
                            my_path = os.path.join(sub_path[prefix:], name).replace('\\', '/').lstrip('/')
                            if my_path.lower() not in filenames:
                                lines.append('  * %s' % my_path)
                    
                    if len(lines) > 0:
                        mod.check_notes = ['User-added files:\n' + '\n'.join(lines)]

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
        fs2path = center.settings['fs2_path']
        mod = pkg.get_mod()
        modpath = os.path.join(fs2path, mod.folder)
        pkg_files = pkg.filelist
        count = float(len(pkg_files))
        success = 0
        checked = 0
        
        archives = set()
        msgs = []
        
        for info in pkg_files:
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
        
        self.post((pkg, archives, success, checked, msgs))

    def finish(self):
        results = self.get_results()
        #installed = center.installed

        for pkg, archives, s, c, m in results:
            mod = pkg.get_mod()
            
            if s == 0:
                # Not Installed
                # What?!
                logging.warning('Package %s of mod %s (%s) is not installed but in the local repo.' % (pkg.name, mod.mid, mod.title))
            
            if pkg is not None:
                pkg.check_notes = m
                pkg.files_ok = s
                pkg.files_checked = c

        center.signals.repo_updated.emit()


# TODO: Optimize, make sure all paths are relative (no mod should be able to install to C:\evil)
class InstallTask(progress.MultistepTask):
    _pkgs = None
    _pkg_names = None
    _dls = None
    _steps = 2
    mod = None

    def __init__(self, pkgs, mod=None):
        self._pkgs = []
        self._pkg_names = []
        rmods = center.settings['mods']

        if mod is not None:
            self.mod = mod

        # Make sure we have remote mods here!
        for pkg in pkgs:
            mod = pkg.get_mod()
            pkg = rmods.query(pkg)
            self._pkgs.append(pkg)
            self._pkg_names.append((mod.mid, pkg.name))

        super(InstallTask, self).__init__()

        self.done.connect(self.finish)
        progress.update(0, 'Installing mods...')

    def abort(self):
        super(InstallTask, self).abort()

        util.cancel_downloads()

    def finish(self):
        if self.aborted:
            if self._cur_step == 1:
                # Need to remove all those temporary directories.
                for ar in self.get_results():
                    shutil.rmtree(ar['tpath'])
        else:
            mods = set()
            fs2_path = center.settings['fs2_path']

            # Register installed pkgs
            for pkg in self._pkgs:
                logo_path = pkg.get_mod().logo_path
                pkg = center.installed.add_pkg(pkg)
                mod = pkg.get_mod()
                mod.logo_path = logo_path
                mods.add(mod)

            # Generate knossos.json files.
            for mod in mods:
                kpath = os.path.join(fs2_path, mod.folder, 'mod.json')
                logo = os.path.join(fs2_path, mod.folder, 'knossos.' + mod.logo.split('.')[-1])
                
                # Copy the logo right next to the json file.
                shutil.copy(mod.logo_path, logo)
                info = mod.get()
                info['logo'] = os.path.join(logo)

                with open(kpath, 'w') as stream:
                    json.dump(info, stream)

        run_task(CheckTask())

    def init1(self):
        mods = set()
        for pkg in self._pkgs:
            mods.add(pkg.get_mod())

        self._threads = 3
        self.add_work(mods)

    def work1(self, mod):
        fs2_path = center.settings['fs2_path']
        modpath = os.path.join(fs2_path, mod.folder)
        mfiles = mod.get_files()
        mnames = [f['filename'] for f in mfiles]

        archives = set()
        progress.update(0, 'Checking %s...' % mod.title)
        
        kpath = os.path.join(modpath, 'mod.json')
        if os.path.isfile(kpath):
            try:
                with open(kpath, 'r') as stream:
                    info = json.load(stream)
            except:
                logging.exception('Failed to parse mod.json!')
                info = None

            if info is not None and info['version'] != str(mod.version):
                mod.folder += '_kv_' + str(mod.version)
                modpath = os.path.join(fs2_path, mod.folder)

        if mod.folder not in ('', '.') and os.path.isdir(modpath):
            for path, dirs, files in os.walk(modpath):
                relpath = path[len(modpath):].lstrip('/')
                for item in files:
                    itempath = util.pjoin(relpath, item)
                    if itempath not in mnames:
                        logging.info('File "%s" is left over.', itempath)

        for info in mfiles:
            if (mod.mid, info['package']) not in self._pkg_names:
                continue

            itempath = util.ipath(os.path.join(modpath, info['filename']))
            if not os.path.isfile(itempath) or util.gen_hash(itempath) != info['md5sum']:
                archives.add((mod.mid, info['package'], info['archive']))

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

        self._threads = 0
        self.add_work(downloads)

    def work2(self, archive):
        with tempfile.TemporaryDirectory() as tpath:
            arpath = os.path.join(tpath, archive['filename'])
            fs2path = center.settings['fs2_path']
            modpath = os.path.join(fs2path, archive['mod'].folder)

            with open(arpath, 'wb') as stream:
                util.try_download(archive['urls'], stream)

            if self.aborted:
                return

            if archive['is_archive']:
                progress.update(1, 'Extracting %s...' % archive['filename'])

                cpath = os.path.join(tpath, 'content')
                os.mkdir(cpath)
                util.extract_archive(arpath, cpath)

                for item in archive['pkg'].filelist:
                    if item['archive'] != archive['filename']:
                        continue

                    src_path = os.path.join(cpath, item['orig_name'])
                    dest_path = util.ipath(os.path.join(modpath, item['filename']))

                    if not os.path.isfile(src_path):
                        logging.error('Missing file "%s" from archive "%s" for package "%s" (%s)!',
                                      item['orig_name'], archive['filename'], archive['pkg'].name, archive['mod'].title)
                    else:
                        try:
                            dparent = os.path.dirname(dest_path)
                            if not os.path.isdir(dparent):
                                os.makedirs(dparent)

                            shutil.move(src_path, dest_path)
                        except:
                            logging.exception('Failed to move file "%s" from archive "%s" for package "%s" (%s) to its destination %s!',
                                              src_path, archive['filename'], archive['pkg'].name, archive['mod'].title, dest_path)
            else:
                for item in archive['pkg'].filelist:
                    if item['archive'] != archive['filename']:
                        continue

                    dest_path = util.ipath(os.path.join(modpath, archive['filename']))

                    try:
                        dparent = os.path.dirname(dest_path)
                        if not os.path.isdir(dparent):
                            os.makedirs(dparent)

                        shutil.move(arpath, dest_path)
                    except:
                        logging.exception('Failed to move file "%s" from archive "%s" for package "%s" (%s) to its destination %s!',
                                          arpath, archive['filename'], archive['pkg'].name, archive['mod'].title, dest_path)


# TODO: make sure all paths are relative (no mod should be able to install to C:\evil)
class UninstallTask(progress.MultistepTask):
    _pkgs = None
    _steps = 2

    def __init__(self, pkgs):
        super(UninstallTask, self).__init__()

        self._pkgs = []
        for pkg in pkgs:
            try:
                self._pkgs.append(center.installed.query(pkg))
            except repo.ModNotFound:
                logging.exception('Someone tried to uninstall a non-existant package (%s, %s)!', pkg.get_mod().mid, pkg.name)

        self.done.connect(self.finish)
        progress.update(0, 'Uninstalling mods...')

    def init1(self):
        self.add_work(self._pkgs)

    def work1(self, pkg):
        fs2path = center.settings['fs2_path']
        mod = pkg.get_mod()

        for item in pkg.filelist:
            path = util.ipath(os.path.join(fs2path, mod.folder, item['filename']))
            if not os.path.isfile(path):
                logging.warning('File "%s" for mod "%s" (%s) is missing during uninstall!', item['filename'], mod.title, mod.mid)
            else:
                os.unlink(path)

    def init2(self):
        mods = set()

        # Unregister uninstalled pkgs.
        for pkg in self._pkgs:
            mods.add(pkg.get_mod())
            center.installed.del_pkg(pkg)

        self.add_work(mods)

    def work2(self, mod):
        modpath = os.path.join(center.settings['fs2_path'], mod.folder)

        print(mod.title, mod.packages)
        # Remove our files
        if len(mod.packages) == 0:
            my_files = (os.path.join(modpath, 'mod.json'), mod.logo_path)
            for path in my_files:
                if os.path.isfile(path):
                    os.unlink(path)

        # Remove empty directories.
        for path, dirs, files in os.walk(modpath, topdown=False):
            if len(dirs) == 0 and len(files) == 0:
                os.rmdir(path)

    def finish(self):
        run_task(CheckTask())


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
        data = util.get(center.INNOEXTRACT_LINK)
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
            QtGui.QMessageBox.critical(center.main_win.win, 'Error', 'The installer failed! Please read the log for more details...')
            return
        elif results[0] == -1:
            QtGui.QMessageBox.critical(center.main_win.win, 'Error', 'The selected file wasn\'t a proper Inno Setup installer. Are you shure you selected the right file?')
            return
        else:
            QtGui.QMessageBox.information(center.main_win.win, 'Done', 'FS2 was successfully installed.')

        fs2_path = results[0]
        center.settings['fs2_path'] = fs2_path
        center.settings['fs2_bin'] = None
        
        for item in glob.glob(os.path.join(fs2_path, 'fs2_*.exe')):
            if os.path.isfile(item):
                center.settings['fs2_bin'] = os.path.basename(item)
                break
        
        api.save_settings()
        center.main_win.check_fso()


class CheckUpdateTask(progress.Task):

    def __init__(self):
        super(CheckUpdateTask, self).__init__()

        self.add_work(('',))
        progress.update(0, 'Checking for updates...')

    def work(self, item):
        progress.update(0, 'Checking for updates...')

        update_base = util.pjoin(center.UPDATE_LINK, center.settings['update_channel'])
        version = util.get(update_base + '/version?me=' + center.VERSION)

        try:
            version = semantic_version.Version(version)
        except:
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
        progress.update(0, 'Installing update...')

    def work(self, item):
        # Download it.
        update_base = center.settings['update_link']

        dir_name = tempfile.mkdtemp()
        updater = os.path.join(dir_name, 'knossos_updater.exe')
        
        progress.start_task(0, 0.98, 'Downloading update...')
        with open(updater, 'wb') as stream:
            util.download(update_base + '/updater.exe', stream)

        progress.update(0.99, 'Launching updater...')

        try:
            import win32api
            win32api.ShellExecute(0, 'open', updater, '/D=' + os.getcwd(), os.path.dirname(updater), 1)
        except:
            logging.exception('Failed to launch updater!')
            self.post(False)
        else:
            self.post(True)
            center.app.quit()

    def finish(self):
        res = self.get_results()

        if len(res) < 1 or not res[0]:
            QtGui.QMessageBox.critical(center.app.activeWindow(), 'Knossos', 'Failed to launch the update!')


def run_task(task, cb=None):
    def wrapper():
        cb(task.get_results())
    
    if cb is not None:
        task.done.connect(wrapper)
    
    center.main_win.progress_win.add_task(task)
    center.pmaster.add_task(task)
    center.signals.task_launched.emit(task)
    return task
