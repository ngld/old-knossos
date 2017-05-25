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

"""comtypes.client._code_cache helper module.
This is a simplified version which only allows read-only access to the cache.
"""

import sys
import logging
import types

logger = logging.getLogger(__name__)


def _find_gen_dir():
    _create_comtypes_gen_package()
    return None


def _create_comtypes_gen_package():
    """Import (creating it if needed) the comtypes.gen package."""
    try:
        import comtypes.gen
        logger.info("Imported existing %s", comtypes.gen)
    except ImportError:
        import comtypes
        logger.info("Could not import comtypes.gen, trying to create it.")
        
        module = sys.modules["comtypes.gen"] = types.ModuleType("comtypes.gen")
        comtypes.gen = module
        comtypes.gen.__path__ = []
        logger.info("Created a memory-only package.")
