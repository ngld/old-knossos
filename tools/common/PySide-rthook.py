import os
import sys

path = os.path.join(sys._MEIPASS, 'plugins')

if 'QT_PLUGIN_PATH' in os.environ:
    os.environ['QT_PLUGIN_PATH'] = ''
    del os.environ['QT_PLUGIN_PATH']

from PySide.QtCore import QCoreApplication
QCoreApplication.setLibraryPaths([os.path.abspath(path)])
