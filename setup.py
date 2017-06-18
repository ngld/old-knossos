#!/usr/bin/python
## Copyright 2015 Knossos authors, see NOTICE file
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
from setuptools import setup
from codecs import open  # To use a consistent encoding
from os import path
import re

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Grab the current version
with open(path.join(here, 'knossos', 'center.py'), 'r', encoding='utf-8') as f:
    m = re.search(r"VERSION = '([^']+)'", f.read())
    if m:
        version = m.group(1)
    else:
        version = 'XXX'

if len(sys.argv) == 2 and sys.argv[1] == 'get_version':
    print(version)
    sys.exit(0)


pkg_data = {
    'knossos': ['data/*']
}

# Bundle the html files only for the dev versions
if '-dev' in version:
    pkg_data['knossos'].extend(['../html/*.html', '../html/css/*', '../html/fonts/*', '../html/js/*'])

setup(
    name='knossos',

    # This version should comply with PEP440 (http://legacy.python.org/dev/peps/pep-0440/).
    # The first three numbers should be the same as VERSION in knossos/center.py.
    version=version,

    description='A simple mod manager for FreeSpace 2 Open',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/ngld/knossos',

    # Author details
    author='ngld',
    author_email='ngld@tproxy.de',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',

        # Supported Python versions
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ],

    keywords='fso freespace',
    packages=['knossos', 'knossos.ui', 'knossos.third_party'],
    install_requires=['six', 'requests', 'semantic_version', 'raven', 'PyQt5'],

    # List additional groups of dependencies here (e.g. development dependencies).
    # You can install these using the following syntax, for example:
    # $ pip install -e .[dev,test]
    extras_require={
    },

    package_data=pkg_data,

    data_files=[],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'gui_scripts': [
            'knossos=knossos.launcher:main',
        ]
    }
)
