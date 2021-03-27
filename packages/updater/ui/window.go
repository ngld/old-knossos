package ui

import (
	"fmt"
	"time"

	"github.com/inkyblackness/imgui-go/v4"
)

type LogLevel int

const (
	LogDebug LogLevel = iota
	LogInfo
	LogWarn
	LogError
)

type logItem struct {
	timestamp string
	message   string
	level     LogLevel
}

var (
	logLines       = make([]logItem, 0)
	autoScroll     = true
	progressStatus = "Initialising..."
	progress       = float32(0.0)
)

func Render() {
	viewport := imgui.MainViewport()
	imgui.SetNextWindowPos(imgui.Vec2{
		X: 0,
		Y: 0,
	})
	imgui.SetNextWindowSize(viewport.Size())

	imgui.BeginV("Default", nil, imgui.WindowFlagsNoDecoration|imgui.WindowFlagsNoMove|imgui.WindowFlagsNoResize|imgui.WindowFlagsNoSavedSettings)

	imgui.Text(progressStatus)
	imgui.ProgressBar(progress)
	imgui.Spacing()

	if imgui.Button("Clear") {
		logLines = make([]logItem, 0)
	}

	imgui.SameLine()
	imgui.Checkbox("Auto-scroll", &autoScroll)

	imgui.Separator()
	imgui.BeginChildV("LogScrollArea", imgui.Vec2{X: 0, Y: -5}, true, imgui.WindowFlagsAlwaysVerticalScrollbar)
	// tweak line padding
	imgui.PushStyleVarVec2(imgui.StyleVarItemSpacing, imgui.Vec2{X: 4, Y: 1})

	for _, line := range logLines {
		var color imgui.Vec4
		switch line.level {
		case LogDebug:
			color = imgui.Vec4{X: 1, Y: 1, Z: 1, W: 0.5}
		case LogInfo:
			color = imgui.Vec4{X: 1, Y: 1, Z: 1, W: 1.0}
		case LogWarn:
			color = imgui.Vec4{X: 1, Y: 1, Z: 0.5, W: 1}
		case LogError:
			color = imgui.Vec4{X: 1, Y: 0, Z: 0, W: 1}
		}

		imgui.PushStyleColor(imgui.StyleColorText, color)

		imgui.PushFont(PtMonoFont)
		imgui.Text(fmt.Sprintf("[%s]", line.timestamp))
		imgui.PopFont()

		imgui.SameLine()
		imgui.Text(line.message)

		imgui.PopStyleColor()
	}

	if autoScroll && imgui.ScrollY() >= imgui.ScrollMaxY() {
		imgui.SetScrollHereY(1.0)
	}

	imgui.PopStyleVar()
	imgui.EndChild()

	imgui.End()
}

func SetProgress(fraction float32, status string) {
	progress = fraction
	progressStatus = status
}

func Log(level LogLevel, message string, args ...interface{}) {
	logLines = append(logLines, logItem{
		timestamp: time.Now().Format(time.Kitchen),
		level:     level,
		message:   fmt.Sprintf(message, args...),
	})
}
