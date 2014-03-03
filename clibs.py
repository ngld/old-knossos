## Copyright 2014 ngld <ngld@tproxy.de>
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

import logging
import ctypes.util


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


def load_lib(*names):
    exc = None
    
    for name in names:
        if '.' not in name:
            name = ctypes.util.find_library(name)
            if name is None:
                continue
        
        try:
            return ctypes.cdll.LoadLibrary(name)
        except OSError as e:
            if exc is None:
                exc = e
    
    raise Exception(names[0] + ' could not be found!')


def double_zero_string(val):
    global alc
    
    off = 0
    data = []
    while val and val[off]:
        slen = alc.strlen(val)
        if val[off] == b'\x00':
            break
        
        data.append(val[off:off + slen].decode('utf8'))
        off += slen
    
    return data

# Load SDL
try:
    sdl = load_lib('libSDL-1.2.so.0', 'SDL')
    SDL2 = False
except:
    # Try SDL 2
    sdl = load_lib('libSDL2.so', 'SDL2')
    SDL2 = True

# SDL constants
if SDL2:
    SDL_INIT_VIDEO = 0x00000020
    SDL_INIT_JOYSTICK = 0x00000200
    SDL_WINDOW_FULLSCREEN = 0x00000001
    
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

# OpenAL constants
ALC_DEFAULT_DEVICE_SPECIFIER = 0x1004
ALC_DEVICE_SPECIFIER = 0x1005
ALC_CAPTURE_DEVICE_SPECIFIER = 0x310
ALC_CAPTURE_DEFAULT_DEVICE_SPECIFIER = 0x311

# Load OpenAL
alc = load_lib('libopenal.so.1.15.1', 'openal', 'OpenAL')
alc.alcIsExtensionPresent.restype = ctypes.c_bool
alc.alcGetString.restype = ctypes.POINTER(ctypes.c_char)


if SDL2:
    # TODO: This causes a segfault once the script ends.
    # (It's caused by an invalid read in pthread_mutex_lock() which is called XCloseDisplay()
    #  which in turn is called by QApplication's destructor.)
    # I guess both SDL and Qt are closing the display, thus causing a double-free.
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
            joys.append(sdl.SDL_JoystickNameForIndex(i))
        
        sdl.SDL_QuitSubSystem(SDL_INIT_JOYSTICK)
        return joys
else:
    def get_modes():
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

    def list_joysticks():
        if sdl.SDL_InitSubSystem(SDL_INIT_JOYSTICK) < 0:
            logging.error('Failed to init SDL\'s joystick subsystem!')
            logging.error(sdl.SDL_GetError())
            return []
        
        joys = []
        for i in range(sdl.SDL_NumJoysticks()):
            joys.append(sdl.SDL_JoystickName(i).decode('utf8'))
        
        sdl.SDL_QuitSubSystem(SDL_INIT_JOYSTICK)
        return joys


def can_detect_audio():
    # OpenAL Soft doesn't support ALC_ENUMERATION_EXT but still provides a reasonable
    # list. For now, I'll pretend this extension is always present.
    return True  # alc.alcIsExtensionPresent(None, 'ALC_ENUMERATION_EXT')


def list_audio_devs():
    devs = double_zero_string(alc.alcGetString(None, ALC_DEVICE_SPECIFIER))
    default = alc.alcGetString(None, ALC_DEFAULT_DEVICE_SPECIFIER)
    
    captures = double_zero_string(alc.alcGetString(None, ALC_CAPTURE_DEVICE_SPECIFIER))
    default_capture = alc.alcGetString(None, ALC_CAPTURE_DEFAULT_DEVICE_SPECIFIER)
    
    default = ctypes.cast(default, ctypes.c_char_p).value.decode('utf8')
    default_capture = ctypes.cast(default_capture, ctypes.c_char_p).value.decode('utf8')
    
    return devs, default, captures, default_capture
