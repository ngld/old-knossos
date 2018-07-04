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
import os.path
import logging
import ctypes.util
import threading
from . import uhf
uhf(__name__)

from . import center

if sys.platform == 'win32':
    ENCODING = 'latin1'
else:
    ENCODING = 'utf8'

sdl = None
alc = None

sdl_init_lock = threading.Lock()
alc_init_lock = threading.Lock()


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


class SDL_JoystickGUID(ctypes.Structure):
    _fields_ = [
        ('data1', ctypes.c_uint8 * 8),
        ('data2', ctypes.c_uint8 * 8)
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

        end = off + 1
        while val[end] != b'\x00':
            end += 1

        data.append(val[off:end].decode(ENCODING, 'replace'))
        off = end + 1

    return data


def init_sdl():
    global sdl, get_modes, list_joysticks, list_guid_joysticks, get_config_path

    with sdl_init_lock:
        if sdl:
            return

        if center.settings['sdl2_path']:
            try:
                sdl = load_lib(center.settings['sdl2_path'])
            except Exception:
                logging.exception('Failed to load user-supplied SDL2!')

        if not sdl:
            # Load SDL
            if sys.platform == 'darwin' and hasattr(sys, 'frozen'):
                try:
                    sdl = load_lib('../Frameworks/SDL2.framework/SDL2')
                except Exception:
                    logging.exception('Failed to load bundled SDL2!')

        if not sdl:
            sdl = load_lib('libSDL2-2.0.so.0', 'SDL2', 'SDL2.dll', 'libSDL2.dylib')

        # SDL constants
        SDL_INIT_VIDEO = 0x00000020
        SDL_INIT_JOYSTICK = 0x00000200

        # SDL.h
        sdl.SDL_SetMainReady.argtypes = []
        sdl.SDL_SetMainReady.restype = None

        sdl.SDL_Init.argtypes = [ctypes.c_uint32]
        sdl.SDL_Init.restype = ctypes.c_int

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

        sdl.SDL_JoystickGetDeviceGUID.argtypes = [ctypes.c_int]
        sdl.SDL_JoystickGetDeviceGUID.restype = SDL_JoystickGUID

        sdl.SDL_JoystickGetGUIDString.argtypes = [SDL_JoystickGUID, ctypes.c_char_p, ctypes.c_int]
        sdl.SDL_JoystickGetGUIDString.restype = None

        # SDL_filesystem.h
        sdl.SDL_GetPrefPath.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        sdl.SDL_GetPrefPath.restype = ctypes.c_char_p

        sdl.SDL_SetMainReady()
        if sdl.SDL_Init(0) != 0:
            logging.error('Failed to init SDL!')
            logging.error(sdl.SDL_GetError())

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

        def list_guid_joysticks():
            if sdl.SDL_InitSubSystem(SDL_INIT_JOYSTICK) < 0:
                logging.error('Failed to init SDL\'s joystick subsystem!')
                logging.error(sdl.SDL_GetError())
                return []

            joys = []
            buf = ctypes.create_string_buffer(33)
            for i in range(sdl.SDL_NumJoysticks()):
                guid = sdl.SDL_JoystickGetDeviceGUID(i)
                sdl.SDL_JoystickGetGUIDString(guid, buf, 33)

                guid_str = buf.raw.decode(ENCODING).strip('\x00')
                name = sdl.SDL_JoystickNameForIndex(i).decode(ENCODING)
                joys.append((guid_str, i, name))

            sdl.SDL_QuitSubSystem(SDL_INIT_JOYSTICK)
            return joys

        def get_config_path():
            # See https://github.com/scp-fs2open/fs2open.github.com/blob/master/code/osapi/osapi.cpp
            return sdl.SDL_GetPrefPath(b'HardLightProductions', b'FreeSpaceOpen').decode('utf8')


# OpenAL constants
ALC_DEFAULT_DEVICE_SPECIFIER = 0x1004
ALC_DEVICE_SPECIFIER = 0x1005
ALC_ALL_DEVICES_SPECIFIER = 0x1013
ALC_CAPTURE_DEVICE_SPECIFIER = 0x310
ALC_CAPTURE_DEFAULT_DEVICE_SPECIFIER = 0x311


def init_openal():
    global alc, dev, ctx

    with alc_init_lock:
        if alc:
            return

        # Load OpenAL
        if center.settings['openal_path']:
            try:
                alc = load_lib(center.settings['openal_path'])
            except Exception:
                logging.exception('Failed to load user-supplied OpenAL!')

        if not alc:
            try:
                alc = load_lib('libopenal.so.1.15.1', 'openal', 'OpenAL', 'OpenAL32.dll')
            except Exception:
                logging.exception('Failed to load OpenAL!')

        if alc:
            alc.alcOpenDevice.argtypes = [ctypes.c_char_p]
            alc.alcOpenDevice.restype = ctypes.c_void_p

            alc.alcCreateContext.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            alc.alcCreateContext.restype = ctypes.c_void_p

            alc.alcMakeContextCurrent.argtypes = [ctypes.c_void_p]
            alc.alcMakeContextCurrent.restype = ctypes.c_bool

            alc.alcDestroyContext.argtypes = [ctypes.c_void_p]
            alc.alcDestroyContext.restype = None

            alc.alcCloseDevice.argtypes = [ctypes.c_void_p]
            alc.alcCloseDevice.restype = None

            alc.alcGetError.argtypes = [ctypes.c_void_p]
            alc.alcGetError.restype = ctypes.c_char_p

            alc.alcIsExtensionPresent.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            alc.alcIsExtensionPresent.restype = ctypes.c_bool

            alc.alcGetString.argtypes = [ctypes.c_void_p, ctypes.c_int]
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
    except Exception:
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
    return alc.alcIsExtensionPresent(None, b'ALC_ENUMERATION_EXT')


def list_audio_devs():
    if not alc:
        return [], '', [], ''

    if alc.alcIsExtensionPresent(None, b'ALC_ENUMERATE_ALL_EXT'):
        spec = ALC_ALL_DEVICES_SPECIFIER
    else:
        spec = ALC_DEVICE_SPECIFIER

    devs = double_zero_string(alc.alcGetString(None, spec))
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


def list_voices():
    if sys.platform != 'win32':
        return []

    try:
        import win32com.client as cc
        voice = cc.Dispatch('SAPI.SpVoice')
        return [v.GetDescription() for v in voice.GetVoices()]
    except Exception:
        logging.exception('Failed to retrieve voices!')
        return []


def speak(voice, volume, text):
    if sys.platform != 'win32':
        return False

    try:
        import win32com.client as cc

        hdl = cc.Dispatch('SAPI.SpVoice')

        # We always seem to receive an AttributeError when we try to access
        # SetVoice the first time. It works the second time for whatever reason... >_>
        try:
            hdl.SetVoice
        except AttributeError:
            pass

        hdl.SetVoice(hdl.GetVoices()[voice])
        hdl.Volume = volume
        hdl.Speak(text, 19)
        hdl.WaitUntilDone(10000)

        return True
    except Exception:
        logging.exception('Failed to speak!')
        return False
