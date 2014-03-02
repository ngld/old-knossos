import ctypes.util
import atexit


class SDL_Rect(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_int16),
        ('y', ctypes.c_int16),
        ('w', ctypes.c_uint16),
        ('h', ctypes.c_uint16)
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


def check_result(val):
    if val != 0:
        raise sdl.SDL_GetError()


# TODO: Fix this.
def double_zero_string(val):
    global alc
    
    val = ctypes.cast(val, ctypes.POINTER(ctypes.c_char))
    off = 0
    data = []
    while val and val[off]:
        slen = alc.strlen(val[off])
        data.append(val[off:off + slen])
        
        off += slen
    
    #alc.free(val)
    return data


# SDL constants
SDL_INIT_VIDEO    = 0x00000020
SDL_INIT_JOYSTICK = 0x00000200
SDL_HWSURFACE     = 0x00000001
SDL_FULLSCREEN    = 0x80000000

# Load SDL
sdl = load_lib('SDL', 'libSDL-1.2.so.0')
sdl.SDL_GetError.restype = ctypes.c_char_p
sdl.SDL_Init.restype = check_result
sdl.SDL_ListModes.restype = ctypes.POINTER(ctypes.POINTER(SDL_Rect))
sdl.SDL_JoystickName.restype = ctypes.c_char_p

# Init SDL
sdl.SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK)
atexit.register(sdl.SDL_Quit)

# OpenAL constants
ALC_DEFAULT_DEVICE_SPECIFIER         = 0x1004
ALC_DEVICE_SPECIFIER                 = 0x1005
ALC_CAPTURE_DEVICE_SPECIFIER         = 0x310
ALC_CAPTURE_DEFAULT_DEVICE_SPECIFIER = 0x311

# Load OpenAL
alc = load_lib('openal', 'OpenAL')
#alc.alcIsExtensionPresent.argtypes = (ctypes.c_int, ctypes.c_char_p)
alc.alcIsExtensionPresent.restype = ctypes.c_bool
#alc.alcGetString.argtypes = (ctypes.c_int, ctypes.c_int)
alc.alcGetString.restype = double_zero_string


def get_modes():
    modes = sdl.SDL_ListModes(None, SDL_FULLSCREEN | SDL_HWSURFACE)

    for mode in modes:
        if not mode:
            break
        
        rect = mode[0]
        yield (rect.w, rect.h)


def list_joysticks():
    joys = []
    for i in range(sdl.SDL_NumJoysticks()):
        joys.append(sdl.SDL_JoystickName(i))
    
    return joys


def can_detect_audio():
    # Hmm, actually not allowed to pass NULL to alcIsExtensionPresent..
    # how is this supposed to work? -> Hellzed: same question. Weird.
    return True #alc.alcIsExtensionPresent(None, 'ALC_ENUMERATION_EXT')


def list_audio_devs():
    devs = alc.alcGetString(None, ALC_DEVICE_SPECIFIER)
    default = alc.alcGetString(None, ALC_DEFAULT_DEVICE_SPECIFIER)[0]
    
    captures = alc.alcGetString(None, ALC_CAPTURE_DEVICE_SPECIFIER)
    default_capture = alc.alcGetString(None, ALC_CAPTURE_DEFAULT_DEVICE_SPECIFIER)[0]
    
    print(devs, default, captures, default_capture)
    return devs, default, captures, default_capture
