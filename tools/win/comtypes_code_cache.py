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
