package ui

import (
	"runtime"

	"github.com/inkyblackness/imgui-go/v4"
	"github.com/rotisserie/eris"
	"github.com/veandco/go-sdl2/sdl"
)

func RunApp(title string, width, height int32) error {
	// Avoid threading issues around cgo / C
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	err := sdl.Init(sdl.INIT_VIDEO)
	if err != nil {
		return eris.Wrap(err, "failed to initialise SDL2")
	}
	defer sdl.Quit()

	window, err := sdl.CreateWindow(title, sdl.WINDOWPOS_CENTERED, sdl.WINDOWPOS_CENTERED, width, height, sdl.WINDOW_OPENGL|sdl.WINDOW_RESIZABLE|sdl.WINDOW_ALLOW_HIGHDPI)
	if err != nil {
		return eris.Wrap(err, "failed to create window")
	}
	defer window.Destroy()

	context := imgui.CreateContext(nil)
	defer context.Destroy()
	io := imgui.CurrentIO()

	// Disable ImGui's default ini settings store
	io.SetIniFilename("")
	initKeyMapping(io)
	loadFont(io)

	if runtime.GOOS == "darwin" {
		// Always required on Mac
		sdl.GLSetAttribute(sdl.GL_CONTEXT_FLAGS, sdl.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG)
	} else {
		sdl.GLSetAttribute(sdl.GL_CONTEXT_FLAGS, 0)
	}

	sdl.GLSetAttribute(sdl.GL_CONTEXT_PROFILE_MASK, sdl.GL_CONTEXT_PROFILE_CORE)
	sdl.GLSetAttribute(sdl.GL_CONTEXT_MAJOR_VERSION, 3)
	sdl.GLSetAttribute(sdl.GL_CONTEXT_MINOR_VERSION, 2)

	sdl.GLSetAttribute(sdl.GL_DOUBLEBUFFER, 1)
	sdl.GLSetAttribute(sdl.GL_DEPTH_SIZE, 24)
	sdl.GLSetAttribute(sdl.GL_STENCIL_SIZE, 8)

	glCtx, err := window.GLCreateContext()
	if err != nil {
		return eris.Wrap(err, "failed to create OpenGL context")
	}

	err = window.GLMakeCurrent(glCtx)
	if err != nil {
		return eris.Wrap(err, "failed to make the OpenGL context current")
	}

	sdl.GLSetSwapInterval(1)
	renderer, err := NewOpenGL3(io)
	if err != nil {
		return eris.Wrap(err, "failed to initialise OpenGL3 renderer")
	}

	lastTime := uint64(0)
	buttonsDown := make([]bool, 3)
	running := true

	for running {
		// Process events
		for event := sdl.PollEvent(); event != nil; event = sdl.PollEvent() {
			switch event.GetType() {
			case sdl.QUIT:
				running = false
			case sdl.MOUSEWHEEL:
				wheelEvent := event.(*sdl.MouseWheelEvent)
				var deltaX, deltaY float32
				if wheelEvent.X > 0 {
					deltaX++
				} else if wheelEvent.X < 0 {
					deltaX--
				}
				if wheelEvent.Y > 0 {
					deltaY++
				} else if wheelEvent.Y < 0 {
					deltaY--
				}
				io.AddMouseWheelDelta(deltaX, deltaY)
			case sdl.MOUSEBUTTONDOWN:
				buttonEvent := event.(*sdl.MouseButtonEvent)
				switch buttonEvent.Button {
				case sdl.BUTTON_LEFT:
					buttonsDown[0] = true
				case sdl.BUTTON_RIGHT:
					buttonsDown[1] = true
				case sdl.BUTTON_MIDDLE:
					buttonsDown[2] = true
				}
			case sdl.TEXTINPUT:
				inputEvent := event.(*sdl.TextInputEvent)
				io.AddInputCharacters(string(inputEvent.Text[:]))
			case sdl.KEYDOWN:
				keyEvent := event.(*sdl.KeyboardEvent)
				io.KeyPress(int(keyEvent.Keysym.Scancode))
				updateKeyModifier(io)
			case sdl.KEYUP:
				keyEvent := event.(*sdl.KeyboardEvent)
				io.KeyRelease(int(keyEvent.Keysym.Scancode))
				updateKeyModifier(io)
			}
		}

		// Update window size in case it was resized
		displayWidth, displayHeight := window.GetSize()
		io.SetDisplaySize(imgui.Vec2{X: float32(displayWidth), Y: float32(displayHeight)})

		frameWidth, frameHeight := window.GLGetDrawableSize()

		// Update time
		freq := sdl.GetPerformanceFrequency()
		curTime := sdl.GetPerformanceCounter()
		if lastTime > 0 {
			io.SetDeltaTime(float32(curTime-lastTime) / float32(freq))
		} else {
			// Assume 1/60 of a second (60 FPS)
			io.SetDeltaTime(1.0 / 60.0)
		}
		lastTime = curTime

		// Update mouse state
		x, y, state := sdl.GetMouseState()
		io.SetMousePosition(imgui.Vec2{X: float32(x), Y: float32(y)})
		for i, button := range []uint32{sdl.BUTTON_LEFT, sdl.BUTTON_RIGHT, sdl.BUTTON_MIDDLE} {
			io.SetMouseButtonDown(i, buttonsDown[i] || (state&sdl.Button(button)) != 0)
			buttonsDown[i] = false
		}

		imgui.NewFrame()
		Render()
		imgui.Render()

		renderer.PreRender([3]float32{0.0, 0.0, 0.0})
		renderer.Render([2]float32{float32(displayWidth), float32(displayHeight)}, [2]float32{float32(frameWidth), float32(frameHeight)}, imgui.RenderedDrawData())
		window.GLSwap()

		// time.Sleep(25 * time.Millisecond)
	}

	return nil
}

func initKeyMapping(io imgui.IO) {
	keyMapping := map[int]int{
		imgui.KeyTab:        sdl.SCANCODE_TAB,
		imgui.KeyLeftArrow:  sdl.SCANCODE_LEFT,
		imgui.KeyRightArrow: sdl.SCANCODE_RIGHT,
		imgui.KeyUpArrow:    sdl.SCANCODE_UP,
		imgui.KeyDownArrow:  sdl.SCANCODE_DOWN,
		imgui.KeyPageUp:     sdl.SCANCODE_PAGEUP,
		imgui.KeyPageDown:   sdl.SCANCODE_PAGEDOWN,
		imgui.KeyHome:       sdl.SCANCODE_HOME,
		imgui.KeyEnd:        sdl.SCANCODE_END,
		imgui.KeyInsert:     sdl.SCANCODE_INSERT,
		imgui.KeyDelete:     sdl.SCANCODE_DELETE,
		imgui.KeyBackspace:  sdl.SCANCODE_BACKSPACE,
		imgui.KeySpace:      sdl.SCANCODE_BACKSPACE,
		imgui.KeyEnter:      sdl.SCANCODE_RETURN,
		imgui.KeyEscape:     sdl.SCANCODE_ESCAPE,
		imgui.KeyA:          sdl.SCANCODE_A,
		imgui.KeyC:          sdl.SCANCODE_C,
		imgui.KeyV:          sdl.SCANCODE_V,
		imgui.KeyX:          sdl.SCANCODE_X,
		imgui.KeyY:          sdl.SCANCODE_Y,
		imgui.KeyZ:          sdl.SCANCODE_Z,
	}

	for imKey, sdlKey := range keyMapping {
		io.KeyMap(imKey, sdlKey)
	}
}

func updateKeyModifier(io imgui.IO) {
	modState := sdl.GetModState()
	mapModifier := func(lMask sdl.Keymod, lKey int, rMask sdl.Keymod, rKey int) (lResult int, rResult int) {
		if (modState & lMask) != 0 {
			lResult = lKey
		}
		if (modState & rMask) != 0 {
			rResult = rKey
		}
		return
	}
	io.KeyShift(mapModifier(sdl.KMOD_LSHIFT, sdl.SCANCODE_LSHIFT, sdl.KMOD_RSHIFT, sdl.SCANCODE_RSHIFT))
	io.KeyCtrl(mapModifier(sdl.KMOD_LCTRL, sdl.SCANCODE_LCTRL, sdl.KMOD_RCTRL, sdl.SCANCODE_RCTRL))
	io.KeyAlt(mapModifier(sdl.KMOD_LALT, sdl.SCANCODE_LALT, sdl.KMOD_RALT, sdl.SCANCODE_RALT))
}
