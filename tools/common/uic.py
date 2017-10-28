#!/bin/env python

import sys
import re
from subprocess import check_call, CalledProcessError

assert len(sys.argv) > 3, 'Usage: uic.py <input file> <output file> <pyuic command>'

in_file = sys.argv[1]
out_file = sys.argv[2]

try:
    check_call(sys.argv[3:] + ['-o', out_file, in_file])
except CalledProcessError as exc:
    sys.exit(exc.returncode)

with open(out_file, 'r') as hdl:
    data = hdl.read()

# Remove imports for resource modules since we don't build any
data = re.sub(r'\nimport res[^\n]+', '', data)

# Remove incorrectly set contentsMargins
data = re.sub(r'\n.*?setContentsMargins\(0, 0, 0, 0\)[^\n]*', '', data)

# Use our shim instead of PyQt5 directly
data = data.replace('from PyQt5 import', 'from ..qt import')
data = data.replace('from QtWebEngineWidgets.QWebEngineView import QWebEngineView', 'from ..qt import QtWebEngineWidgets')
data = data.replace('from QtWebEngineWidgets import QWebEngineView', 'from ..qt import QtWebEngineWidgets')

# Correct references to QWebEngineView
data = data.replace(' QWebEngineView', ' QtWebEngineWidgets.QWebEngineView')

with open(out_file, 'w') as hdl:
    hdl.write(data)
