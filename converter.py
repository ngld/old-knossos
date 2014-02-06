from __future__ import print_function
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')
logging.getLogger().addHandler(logging.FileHandler('converter.log'))

import sys
import os
import argparse
import pickle
import hashlib
import json
import time
import datetime
import signal
import progress
from fso_parser import EntryPoint
from fs2mod import convert_modtree, find_mod, ModInfo2
from qt import QtCore
from six import StringIO


def show_progress(prog, text):
    sys.stdout.write('\r %3d%% %s' % (prog * 100, text))
    sys.stdout.flush()

cache = {
    'mods': {},
    'last_fetch': 0
}
cache_path = os.path.expanduser('~/.fs2mod-py/cache.pick')


def list_modtree(mods, level=0):
    for mod in mods:
        print(' ' * 2 * level + mod.name)
        list_modtree(mod.submods, 1)


def main(args):
    global cache, cache_path
    
    progress.reset()
    progress.set_callback(show_progress)
    
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='action')
    
    list_parser = subs.add_parser('list', help='list mods')
    list_parser.add_argument('--update', action='store_true', default=False, help='update the mod list')
    
    convert_parser = subs.add_parser('convert', help='generates a fs2mod file for one of the listed mods')
    convert_parser.add_argument('modname')
    convert_parser.add_argument('outpath', help='path to the fs2mod file')
    
    json_parser = subs.add_parser('json', help='generate a json file for the passed mods')
    json_parser.add_argument('modname', nargs='+', help='several names of mods or just "all"')
    json_parser.add_argument('-o', dest='outpath', help='output file', type=argparse.FileType('w'), default=sys.stdout)
    json_parser.add_argument('-p', dest='pretty', help='pretty print the output', action='store_true')
    
    args = parser.parse_args(args)
    
    # Load our cache
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as stream:
            try:
                cache = pickle.load(stream)
            except:
                logging.exception('Failed to read the cache at %s!', cache_path)
    
    if args.action == 'list':
        if args.update or len(cache['mods']) == 0:
            logging.info('Fetching current mod list...')
            
            cache['mods'] = EntryPoint.get_mods()
            cache['last_fetch'] = time.time()
            
            # Save the updated cache.
            if not os.path.isdir(os.path.dirname(cache_path)):
                os.makedirs(os.path.dirname(cache_path))
            
            with open(cache_path, 'wb') as stream:
                pickle.dump(cache, stream)
        
        ftime = datetime.datetime.fromtimestamp(cache['last_fetch'])
        print('This list was last updated on ' + ftime.strftime('%c'))
        list_modtree(cache['mods'])
        
    elif args.action == 'convert':
        if os.path.exists(args.outpath):
            logging.error('"%s" already exists! I won\'t overwrite it!', args.outpath)
            return
        
        # Look for the mod...
        mod = find_mod(cache['mods'], args.modname)
        if mod is None:
            logging.error('Couldn\'t find mod "%s"!', args.modname)
            return
        
        logging.info('Converting mod...')
        mod = convert_modtree([mod])[0]
        
        logging.info('Writing fs2mod file...')
        mod.generate_zip(args.outpath)
        
        logging.info('Done!')
    
    elif args.action == 'json':
        # Look for our mods
        
        if 'all' in args.modname:
            mods = cache['mods']
        else:
            mods = []
            for mod in args.modname:
                m = find_mod(cache['mods'], mod)
                if m is None:
                    logging.warning('Mod "%s" was not found!', mod)
                else:
                    mods.append(m)
        
        if len(mods) < 1:
            logging.error('No mods to convert!')
            return
        
        app = QtCore.QCoreApplication([])
        
        class ConvertTask(progress.Task):
            def work(self, mod):
                self.add_work(mod.submods)
                
                result = ModInfo2()
                cur = mod
                while cur.parent is not None:
                    cur = cur.parent
                    if cur.folder != '':
                        result.dependencies.append(cur.folder)
                
                for i, sub in enumerate(mod.submods):
                    mod.submods[i] = sub.name
                
                result.read(mod)
                self.post(result)
        
        master = progress.Master()
        task = ConvertTask()
        task.add_work(mods)
        
        def update_progress():
            total, items = task.get_progress()
            text = []
            for item in items.values():
                text.append('%3d%% %s' % (item[0] * 100, item[1]))
            
            progress.update(total, '\n'.join(text))
        
        def finish():
            app.quit()
        
        task.progress.connect(update_progress)
        task.done.connect(finish)
        
        def core():
            signal.signal(signal.SIGINT, lambda a, b: app.quit())
            master.start_workers(5)
            master.add_task(task)
            app.exec_()
            master.stop_workers()
        
        out = StringIO()
        progress.init_curses(core, out)
        sys.stdout.write(out.getvalue())
        
        mods = {}
        if hasattr(args.outpath, 'name'):
            outpath = args.outpath.name
        else:
            outpath = None
        
        for mod in task.get_results():
            mods[mod.name] = mod.__dict__
            
            if mod.logo is not None:
                if outpath is None:
                    del mods[mod.name]['logo']
                    logging.warning('Skipping logo for "%s" because the output is stdout.', mod.name)
                else:
                    dest = outpath + '.' + hashlib.md5(mod.logo).hexdigest() + '.jpg'
                    with open(dest, 'wb') as stream:
                        stream.write(mod.logo)
                    
                    mods[mod.name]['logo'] = os.path.basename(dest)

            if mod.parent is not None:
                mods[mod.name]['parent'] = mod.parent.name
        
        if args.pretty:
            json.dump(mods, args.outpath, indent=4)
        else:
            json.dump(mods, args.outpath, separators=(',', ':'))

if __name__ == '__main__':
    main(sys.argv[1:])
