import os.path
import comtypes.client as cc

cc.gen_dir = os.path.expandvars(r'$APPDATA\knossos\comtypes')
if not os.path.isdir(cc.gen_dir):
    os.makedirs(cc.gen_dir)
