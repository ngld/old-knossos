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

import sys
import os.path
import re
import json

HTML_RE = re.compile(r'<(?:span data-tr[^>]*>((?:[^<]|<(?!/span))+)</span>|div data-tr[^>]*>((?:[^<]|<(?!/div))+)</div>)')
JS_RE = re.compile(r'tr_table\[(\'[^\']\'|"[^"]+"|`[^`]+`)+\]')


def main(args):
    files = []
    output = None

    while len(args) > 0:
        if args[0] == '-o':
            args.pop(0)
            output = args.pop(0)
        else:
            files.append(args.pop(0))

    if not output or len(files) < 1:
        print('Usage: %s -o <output file> [files...]' % os.path.basename(__file__))
        sys.exit(1)

    msgs = []
    for fn in files:
        if fn.endswith('.html'):
            pat = HTML_RE
        elif fn.endswith('.js'):
            pat = JS_RE
        else:
            print('ERROR: Unknwown file extension: %s' % fn)
            sys.exit(1)

        with open(fn, 'r') as stream:
            data = stream.read()

        for m in pat.finditer(data):
            msgs.append(m.group())

    with open(output, 'w') as stream:
        stream.write('function msg_list() {\n')
        for msg in msgs:
            stream.write('    qsTr(%s);\n' % json.dumps(msg))

        stream.write('}\n\n')
        stream.write('function get_translation_source() {\n')
        stream.write('    return %s;\n}\n' % json.dumps(msgs))


if __name__ == '__main__':
    main(sys.argv[1:])
