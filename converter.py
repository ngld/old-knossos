from __future__ import print_function
import sys
import os
import argparse
import progress
import logging
import pickle
import time
import datetime
from parser import EntryPoint
from fs2mod import convert_modtree, find_mod


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
    
    progress.progress_callback = show_progress
    progress.reset()
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='action')
    
    list_parser = subs.add_parser('list', help='list mods')
    list_parser.add_argument('--update', action='store_true', default=False, help='update the mod list')
    
    convert_parser = subs.add_parser('convert', help='generates a fs2mod file for one of the listed mods')
    convert_parser.add_argument('modname')
    convert_parser.add_argument('outpath', help='path to the fs2mod file')
    
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

if __name__ == '__main__':
    main(sys.argv[1:])
