## Copyright 2014 ngld <ngld@tproxy.de>
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
import threading
import subprocess
import shutil
import glob
import stat
import json
import tempfile

import manager
from lib import util, progress
from lib.repo import Repo
from lib.qt import QtGui


class FetchTask(progress.Task):
    _fs2mod_list = None
    _fs2mod_lock = None
    
    def __init__(self):
        super(FetchTask, self).__init__()
        
        self._fs2mod_list = []
        self._fs2mod_lock = threading.Lock()

        # Remove all logos.
        for path in glob.glob(os.path.join(manager.settings_path, 'logo*.*')):
            if os.path.isfile(path):
                logging.info('Removing old logo "%s"...', path)
                os.unlink(path)
        
        self.done.connect(self.finish)
        self.add_work([(i * 100, link[0]) for i, link in enumerate(manager.settings['repos'])])
    
    def work(self, params):
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
                        if ar['is_archive']:
                            for item in ar['contents']:
                                filelist[util.pjoin(ar['dest'], item)] = (mod.mid, pkg.name)
                        else:
                            filelist[util.pjoin(ar['dest'], name)] = (mod.mid, pkg.name)

            manager.save_settings()
        
        manager.signals.list_updated.emit()


class CheckTask(progress.Task):
    can_abort = False
    
    def __init__(self, mods):
        super(CheckTask, self).__init__()
        
        pkgs = []
        for mod in mods:
            pkgs.extend(mod.packages)

        self.add_work(pkgs)

    def work(self, pkg):
        fs2path = manager.settings['fs2_path']
        modpath = os.path.join(fs2path, pkg.get_mod().folder)
        files = pkg.get_files()
        
        count = float(len(files))
        success = 0
        checked = 0
        
        archives = set()
        msgs = []
        
        for item, info in files.items():
            mypath = util.ipath(os.path.join(fs2path, item))
            fix = False
            if os.path.isfile(mypath):
                progress.update(checked / count, 'Checking "%s"...' % (item))
                
                if util.gen_hash(mypath) == info[0]:
                    success += 1
                else:
                    msgs.append('File "%s" is corrupted. (checksum mismatch)' % (item))
                    fix = True
            else:
                msgs.append('File "%s" is missing.' % (item))
                fix = True
            
            if fix:
                archives.add(info[1])
            
            checked += 1
        
        if pkg.get_mod().folder != '':
            prefix = len(manager.settings['fs2_path'])
            filelist = manager.settings['known_files']
            lines = []
            for sub_path, dirs, files in os.walk(modpath):
                for name in files:
                    my_path = os.path.join(sub_path[prefix:], name).replace('\\', '/').lower().lstrip('/')
                    if my_path not in filelist:
                        lines.append('  * %s' % my_path)
            
            if len(lines) > 0:
                msgs.append('User-added files:\n' + '\n'.join(lines))
        
        self.post((pkg, archives, success, checked, msgs))


class InstallTask(progress.Task):
    _pkgs = None

    def __init__(self, pkgs):
        super(InstallTask, self).__init__()

        mods = set()
        for pkg in pkgs:
            mods.add(pkg.get_mod())

        self._pkgs = pkgs

        self.done.connect(self.finish)
        self.add_work(mods)

    def work(self, mod):
        fs2_path = manager.settings['fs2_path']
        modpath = os.path.join(fs2_path, mod.folder)
        mfiles = mod.get_files()

        archives = set()
        
        if mod.folder != '':
            for path, dirs, files in os.walk(modpath):
                relpath = path[len(modpath):].lstrip('/')
                for item in files:
                    itempath = os.path.join(relpath, item)
                    if itempath not in mfiles:
                        logging.info('File "%s" is left over.', itempath)

        for item, info in mfiles.items():
            itempath = util.ipath(os.path.join(fs2_path, item))
            if not os.path.isfile(itempath) or util.gen_hash(itempath) != info[0]:
                archives.add((mod.mid, info[1]))

        self.post(archives)

    def finish(self):
        archives = set()

        for a in self.get_results():
            archives |= a

        manager.run_task(_InstallTask2(self._pkgs, archives))


class _InstallTask2(progress.Task):
    _pkgs = None

    def __init__(self, pkgs, archives):
        super(_InstallTask2, self).__init__()

        self._pkgs = pkgs

        self.done.connect(self.finish)
        self.add_work([(pkg, archives) for pkg in pkgs])

    def work(self, p):
        pkg, archives = p
        mid = pkg.get_mod().mid
        fs2path = manager.settings['fs2_path']
        files = []

        for f_mid, fname in archives:
            if f_mid == mid and fname in pkg.files:
                files.append(fname)

        count = float(len(files))
        for i, fname in enumerate(files):
            info = pkg.files[fname]
            dest = os.path.join(fs2path, info['dest'])

            progress.start_task(i / count, 1 / count)

            with tempfile.TemporaryDirectory() as tpath:
                arpath = os.path.join(tpath, fname)

                with open(arpath, 'wb') as fobj:
                    util.try_download(info['urls'], fobj)

                if info['is_archive']:
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

    def finish(self):
        manager.run_task(_InstallTask3(self._pkgs))


class _InstallTask3(progress.Task):

    def __init__(self, pkgs):
        super(_InstallTask3, self).__init__()

        mods = set()
        for pkg in pkgs:
            mods.add(pkg.get_mod())

        self.done.connect(self.finish)
        self.add_work(mods)

    def work(self, mod):
        fs2path = manager.settings['fs2_path']

        for act in mod.actions:
            if act['type'] == 'delete':
                for item in act['files']:
                    path = os.path.join(fs2path, item)
                    if os.path.isfile(path):
                        logging.debug('Removing "%s"...', path)
                        os.unlink(path)
            else:
                logging.error('Unknown mod action "%s" in mod "%s" (%s)!', act['type'], mod.title, mod.mid)

    def finish(self):
        manager.update_list()


class UninstallTask(progress.Task):

    def __init__(self, pkgs):
        super(UninstallTask, self).__init__()

        self.done.connect(self.finish)
        self.add_work(pkgs)

    def work(self, pkg):
        fs2path = manager.settings['fs2_path']
        mod = pkg.get_mod()

        for item in pkg.get_files():
            path = util.ipath(os.path.join(fs2path, item))
            if not os.path.isfile(path):
                logging.warning('File "%s" for mod "%s" (%s) is missing during uninstall!', item, mod.title, mod.mid)
            else:
                os.unlink(path)

        # TODO: Remove empty directories.

    def finish(self):
        manager.update_list()


class GOGExtractTask(progress.Task):
    can_abort = False
    
    def __init__(self, gog_path, dest_path):
        super(GOGExtractTask, self).__init__()
        
        self.done.connect(self.finish)
        self.add_work([(gog_path, dest_path)])
    
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
            QtGui.QMessageBox.critical(manager.main_win, 'Error', 'The installer failed! Please read the log for more details...')
            return
        elif results[0] == -1:
            QtGui.QMessageBox.critical(manager.main_win, 'Error', 'The selected file wasn\'t a proper Inno Setup installer. Are you shure you selected the right file?')
            return
        else:
            QtGui.QMessageBox.information(manager.main_win, 'Done', 'FS2 was successfully installed.')

        fs2_path = results[0]
        manager.settings['fs2_path'] = fs2_path
        manager.settings['fs2_bin'] = None
        
        for item in glob.glob(os.path.join(fs2_path, 'fs2_*.exe')):
            if os.path.isfile(item):
                manager.settings['fs2_bin'] = os.path.basename(item)
                break
        
        manager.save_settings()
        manager.init_fs2_tab()
