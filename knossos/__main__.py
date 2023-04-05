#!/usr/bin/python
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

from __future__ import absolute_import, print_function
import sys
import multiprocessing
import os.path

# needed to work properly on windows (due to cpuinfo)
# NOTE: must be first thing executed here
if __name__ == '__main__':
    multiprocessing.freeze_support()

# add third_party to module search path
path = os.path.realpath(os.path.abspath(__file__))
sys.path.insert(1, os.path.join(os.path.dirname(path), 'third_party'))

if __package__ is None and not hasattr(sys, 'frozen'):
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

if len(sys.argv) > 1 and sys.argv[1] == '--cpuinfo':
    # We don't need to initialize knossos if we only need to fetch the CPU info.

    import json
    import cpuinfo

    info = None

    try:
        info = cpuinfo.get_cpu_info_json()
    except Exception:
        from knossos.launcher import logging
        logging.exception('Failed to retrieve CPU info.')

    print(info)
elif len(sys.argv) > 1 and sys.argv[1] == '--run-cpuid':
    import cpuinfo

    print(cpuinfo._get_cpu_info_from_cpuid())
elif len(sys.argv) > 1 and sys.argv[1] == '--deviceinfo':
    import json
    from knossos import clibs

    clibs.init_sdl()
    clibs.init_openal()

    if clibs.can_detect_audio():
        audio_devs = clibs.list_audio_devs()
    else:
        audio_devs = None

    print(json.dumps({
        'modes': clibs.get_modes(),
        'audio_devs': audio_devs,
        'joysticks': clibs.list_joysticks()
    }))
elif len(sys.argv) > 1 and sys.argv[1] == '--fso-config-path':
    from knossos import clibs

    clibs.init_sdl()
    print(clibs.get_config_path())
elif len(sys.argv) > 1 and sys.argv[1] == '--lib-paths':
    import json
    from knossos import clibs, center

    if len(sys.argv) > 3:
        if sys.argv[2] == 'auto':
            center.settings['sdl2_path'] = None
        else:
            center.settings['sdl2_path'] = sys.argv[2]

        if sys.argv[3] == 'auto':
            center.settings['openal_path'] = None
        else:
            center.settings['openal_path'] = sys.argv[3]

    try:
        clibs.init_sdl()
    except Exception:
        clibs.sdl = None

    try:
        clibs.init_openal()
    except Exception:
        clibs.acl = None

    if center.settings['sdl2_path'] and clibs.sdl:
        if clibs.sdl._name != center.settings['sdl2_path']:
            clibs.sdl = None

    if center.settings['openal_path'] and clibs.alc:
        if clibs.alc._name != center.settings['openal_path']:
            clibs.alc = None

    print(json.dumps({
        'sdl2': clibs.sdl._name if clibs.sdl else None,
        'openal': clibs.alc._name if clibs.alc else None
    }))
else:
    from knossos import launcher
    launcher.main()
