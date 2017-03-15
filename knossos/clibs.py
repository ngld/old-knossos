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
import logging
import ctypes.util

from . import uhf
uhf(__name__)

from . import center


ENCODING = 'utf8'
sdl = None
alc = None


class SDL_Rect(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_int16),
        ('y', ctypes.c_int16),
        ('w', ctypes.c_uint16),
        ('h', ctypes.c_uint16)
    ]


class SDL_DisplayMode(ctypes.Structure):
    _fields_ = [
        ('format', ctypes.c_int32),
        ('w', ctypes.c_int),
        ('h', ctypes.c_int),
        ('refresh_rate', ctypes.c_int),
        ('driverdata', ctypes.c_void_p)
    ]


class c_any_pointer(object):

    @classmethod
    def from_param(cls, val):
        return val


def load_lib(*names):
    exc = None

    for name in names:
        if '.' not in name:
            libname = ctypes.util.find_library(name)
            if libname is not None:
                name = libname

        try:
            return ctypes.cdll.LoadLibrary(name)
        except OSError as e:
            if exc is None:
                exc = e

    if exc:
        exc = str(exc)
    else:
        exc = 'Unknown'

    raise Exception(names[0] + ' could not be found! (%s)' % exc)


def double_zero_string(val):
    off = 0
    data = []
    while val and val[off]:
        if val[off] == b'\x00':
            break

        slen = libc.strlen(val)
        data.append(val[off:off + slen].decode(ENCODING, 'replace'))
        off += slen

    return data


def init_sdl():
    global sdl, SDL2, get_modes, list_joysticks, get_config_path

    if center.settings['sdl2_path']:
        try:
            sdl = load_lib(center.settings['sdl2_path'])
            SDL2 = True
        except:
            logging.exception('Failed to load user-supplied SDL2!')

    if not sdl:
        # Load SDL
        if sys.platform == 'darwin' and hasattr(sys, 'frozen'):
            try:
                sdl = load_lib('../Frameworks/SDL2.framework/SDL2')
                SDL2 = True
            except:
                logging.exception('Failed to load bundled SDL2!')

        try:
            sdl = load_lib('libSDL2-2.0.so.0', 'SDL2', 'SDL2.dll', 'libSDL2.dylib')
            SDL2 = True
        except:
            # Try SDL 1.2
            sdl = load_lib('libSDL-1.2.so.0', 'SDL', 'SDL.dll', 'libSDL.dylib')
            SDL2 = False

    # SDL constants
    if SDL2:
        SDL_INIT_VIDEO = 0x00000020
        SDL_INIT_JOYSTICK = 0x00000200

        # SDL.h
        sdl.SDL_InitSubSystem.argtypes = [ctypes.c_uint32]
        sdl.SDL_InitSubSystem.restype = ctypes.c_int

        sdl.SDL_QuitSubSystem.argtypes = [ctypes.c_uint32]
        sdl.SDL_QuitSubSystem.restype = None

        # SDL_error.h
        sdl.SDL_GetError.argtypes = []
        sdl.SDL_GetError.restype = ctypes.c_char_p

        # SDL_video.h
        sdl.SDL_VideoInit.argtypes = [ctypes.c_char_p]
        sdl.SDL_VideoInit.restype = ctypes.c_int

        sdl.SDL_VideoQuit.argtypes = []
        sdl.SDL_VideoQuit.restype = None

        sdl.SDL_GetNumVideoDisplays.argtypes = []
        sdl.SDL_GetNumVideoDisplays.restype = ctypes.c_int

        sdl.SDL_GetNumDisplayModes.argtypes = [ctypes.c_int]
        sdl.SDL_GetNumDisplayModes.restype = ctypes.c_int

        sdl.SDL_GetDisplayMode.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(SDL_DisplayMode)]
        sdl.SDL_GetDisplayMode.restype = ctypes.c_int

        sdl.SDL_GetCurrentDisplayMode.argtypes = [ctypes.c_int, ctypes.POINTER(SDL_DisplayMode)]
        sdl.SDL_GetCurrentDisplayMode.restype = ctypes.c_int

        # SDL_joystick.h
        sdl.SDL_NumJoysticks.argtypes = []
        sdl.SDL_NumJoysticks.restype = ctypes.c_int

        sdl.SDL_JoystickNameForIndex.argtypes = [ctypes.c_int]
        sdl.SDL_JoystickNameForIndex.restype = ctypes.c_char_p

        # SDL_filesystem.h
        sdl.SDL_GetPrefPath.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        sdl.SDL_GetPrefPath.restype = ctypes.c_char_p
    else:
        SDL_INIT_VIDEO = 0x00000020
        SDL_INIT_JOYSTICK = 0x00000200
        SDL_HWSURFACE = 0x00000001
        SDL_FULLSCREEN = 0x80000000

        sdl.SDL_InitSubSystem.argtypes = [ctypes.c_uint32]
        sdl.SDL_InitSubSystem.restype = ctypes.c_int

        sdl.SDL_QuitSubSystem.argtypes = [ctypes.c_uint32]
        sdl.SDL_QuitSubSystem.restype = None

        sdl.SDL_GetError.argtypes = []
        sdl.SDL_GetError.restype = ctypes.c_char_p

        sdl.SDL_ListModes.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        sdl.SDL_ListModes.restype = ctypes.POINTER(ctypes.POINTER(SDL_Rect))

        sdl.SDL_NumJoysticks.argtypes = []
        sdl.SDL_NumJoysticks.restype = ctypes.c_int

        sdl.SDL_JoystickName.argtypes = [ctypes.c_int]
        sdl.SDL_JoystickName.restype = ctypes.c_char_p

    if SDL2:
        def get_modes():
            if sdl.SDL_InitSubSystem(SDL_INIT_VIDEO) < 0 or sdl.SDL_VideoInit(None) < 0:
                logging.error('Failed to init SDL\'s video subsystem!')
                logging.error(sdl.SDL_GetError())
                return []

            modes = []
            for i in range(sdl.SDL_GetNumVideoDisplays()):
                for a in range(sdl.SDL_GetNumDisplayModes(i)):
                    m = SDL_DisplayMode()
                    sdl.SDL_GetDisplayMode(i, a, ctypes.byref(m))

                    if (m.w, m.h) not in modes:
                        modes.append((m.w, m.h))

            sdl.SDL_VideoQuit()
            sdl.SDL_QuitSubSystem(SDL_INIT_VIDEO)
            return modes

        def list_joysticks():
            if sdl.SDL_InitSubSystem(SDL_INIT_JOYSTICK) < 0:
                logging.error('Failed to init SDL\'s joystick subsystem!')
                logging.error(sdl.SDL_GetError())
                return []

            joys = []
            for i in range(sdl.SDL_NumJoysticks()):
                joys.append(sdl.SDL_JoystickNameForIndex(i).decode(ENCODING))

            sdl.SDL_QuitSubSystem(SDL_INIT_JOYSTICK)
            return joys

        def get_config_path():
            # See https://github.com/scp-fs2open/fs2open.github.com/blob/master/code/osapi/osapi.cpp
            return sdl.SDL_GetPrefPath(b'HardLightProductions', b'FreeSpaceOpen').decode('utf8')
    else:
        def get_modes():
            try:
                if sdl.SDL_InitSubSystem(SDL_INIT_VIDEO) < 0:
                    logging.error('Failed to init SDL\'s video subsystem!')
                    logging.error(sdl.SDL_GetError())
                    return []

                modes = sdl.SDL_ListModes(None, SDL_FULLSCREEN | SDL_HWSURFACE)
                my_modes = []

                for mode in modes:
                    if not mode:
                        break

                    rect = mode[0]
                    my_modes.append((rect.w, rect.h))

                sdl.SDL_QuitSubSystem(SDL_INIT_VIDEO)
                return my_modes
            except:
                logging.exception('Failed to call SDL_ListModes()!')
                return []

        def list_joysticks():
            try:
                if sdl.SDL_InitSubSystem(SDL_INIT_JOYSTICK) < 0:
                    logging.error('Failed to init SDL\'s joystick subsystem!')
                    logging.error(sdl.SDL_GetError())
                    return []

                joys = []
                for i in range(sdl.SDL_NumJoysticks()):
                    joys.append(sdl.SDL_JoystickName(i).decode(ENCODING, 'replace'))

                sdl.SDL_QuitSubSystem(SDL_INIT_JOYSTICK)
                return joys
            except:
                logging.exception('Failed to ask SDL for joysticks!')
                return []

        def get_config_path():
            return None


# OpenAL constants
ALC_DEFAULT_DEVICE_SPECIFIER = 0x1004
ALC_DEVICE_SPECIFIER = 0x1005
ALC_CAPTURE_DEVICE_SPECIFIER = 0x310
ALC_CAPTURE_DEFAULT_DEVICE_SPECIFIER = 0x311


def init_openal():
    global alc

    # Load OpenAL
    if center.settings['openal_path']:
        try:
            alc = load_lib(center.settings['openal_path'])
        except:
            logging.exception('Failed to load user-supplied OpenAL!')

    if not alc:
        try:
            alc = load_lib('libopenal.so.1.15.1', 'openal', 'OpenAL')
        except:
            logging.exception('Failed to load OpenAL!')

    if alc:
        alc.alcIsExtensionPresent.restype = ctypes.c_bool
        alc.alcGetString.restype = ctypes.POINTER(ctypes.c_char)
        return True
    else:
        return False


gtk = None
gobject = None


def init_gtk():
    global gtk, gobject

    if gtk:
        return True

    # Load GTK2
    try:
        gtk = load_lib('libgtk-x11-2.0.so.0', 'gtk-x11-2.0')
        gobject = load_lib('libgobject-2.0.so.0', 'gobject-2.0')
    except:
        logging.exception('Failed to load GTK!')

        # Maybe GTK isn't used.
        gtk = None
        gobject = None
    else:
        gtk.gtk_init_check.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p))]
        gtk.gtk_init_check.restype = ctypes.c_bool

        gtk.gtk_settings_get_default.argtypes = []
        gtk.gtk_settings_get_default.restype = ctypes.c_void_p

        gobject.g_object_get.argtypes = [ctypes.c_void_p, ctypes.c_char_p, c_any_pointer, ctypes.c_void_p]
        gobject.g_object_get.restype = None

        gobject.g_free.argtypes = [ctypes.c_void_p]
        gobject.g_free.restype = None

        gobject.g_object_unref.argtypes = [ctypes.c_void_p]
        gobject.g_object_unref.restype = None

        if not gtk.gtk_init_check(None, None):
            logging.error('Failed to initialize GTK!')
        else:
            return True

    return False


def can_detect_audio():
    # OpenAL Soft doesn't support ALC_ENUMERATION_EXT but still provides a reasonable
    # list. For now, I'll pretend this extension is always present.
    return True  # alc.alcIsExtensionPresent(None, 'ALC_ENUMERATION_EXT')


def list_audio_devs():
    devs = double_zero_string(alc.alcGetString(None, ALC_DEVICE_SPECIFIER))
    default = alc.alcGetString(None, ALC_DEFAULT_DEVICE_SPECIFIER)

    captures = double_zero_string(alc.alcGetString(None, ALC_CAPTURE_DEVICE_SPECIFIER))
    default_capture = alc.alcGetString(None, ALC_CAPTURE_DEFAULT_DEVICE_SPECIFIER)

    default = ctypes.cast(default, ctypes.c_char_p).value.decode(ENCODING, 'replace')
    default_capture = ctypes.cast(default_capture, ctypes.c_char_p).value.decode(ENCODING, 'replace')

    return devs, default, captures, default_capture


def g_object_get_string(obj, prop):
    prop = ctypes.c_char_p(prop.encode('utf8'))
    value = ctypes.c_char_p()

    gobject.g_object_get(obj, prop, ctypes.byref(value), 0)

    py_value = value.value
    if py_value:
        py_value = py_value.decode('utf8', 'replace')

    gobject.g_free(value)
    return py_value


def get_gtk_theme():
    global gtk, gobject

    if not gtk:
        return ''

    settings = gtk.gtk_settings_get_default()
    if settings:
        return g_object_get_string(settings, 'gtk-theme-name')
    else:
        return None


if sys.platform == 'win32':
    libc = ctypes.cdll.msvcrt
else:
    libc = load_lib('c')
