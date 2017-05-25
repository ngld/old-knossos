#!/bin/env python

import sys
import os.path
from subprocess import check_call, CalledProcessError

assert len(sys.argv) > 3, 'Usage: rcc.py <path to rcc> <output file> <files ...>'

rcc = sys.argv[1]
output = sys.argv[2]
files = sys.argv[3:]

out = '<!DOCTYPE RCC><RCC version="1.0">'
out += '<qresource>'

for path in files:
    if os.path.basename(path) == 'hlp.png':
        out += '<file alias="hlp.png">%s</file>' % os.path.abspath(path)
    else:
        out += '<file alias="%s">%s</file>' % (path, os.path.abspath(path))

out += '</qresource>'
out += '</RCC>'

qrc_path = output.replace('.rcc', '.qrc')
with open(qrc_path, 'w') as hdl:
    hdl.write(out)

try:
    check_call([rcc, '-binary', qrc_path, '-o', output])
except CalledProcessError as exc:
    sys.exit(exc.returncode)

os.unlink(qrc_path)
