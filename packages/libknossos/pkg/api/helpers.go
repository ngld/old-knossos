package api

import (
	"context"
	"fmt"
	"io"
	"runtime"
	"strings"
	"time"

	"github.com/ngld/knossos/packages/api/client"
	"github.com/rotisserie/eris"
)

// LogLevel indicates the severity of a log message
type LogLevel int

const (
	LogInfo LogLevel = iota + 1
	LogWarn
	LogError
	LogFatal
)

var byteUnits = []string{
	"bytes",
	"KiB",
	"MiB",
	"GiB",
}

type KnossosCtxParams struct {
	// LogCallback is a function that records the passed message in the host application's logging system
	LogCallback func(LogLevel, string, ...interface{})
	// MessageCallback receives progress and status messages which provide details for ongoing tasks
	MessageCallback func(*client.ClientSentEvent) error
	SettingsPath    string
	ResourcePath    string
}

type TaskStep struct {
	Description string
	Ref         uint32
	From        float32
	To          float32
}

type (
	knKey struct{}
)

// FormatBytes returns the passed bytes as a human readable string
func FormatBytes(bytes float64) string {
	size := 0
	for size < len(byteUnits) {
		if bytes < 1024 {
			break
		}

		bytes /= 1024
		size++
	}

	return fmt.Sprintf("%.2f %s", bytes, byteUnits[size])
}

// WithKnossosContext stores the passed callbacks in the context which allows it to be used with Log() and DispatchMessage()
func WithKnossosContext(ctx context.Context, params KnossosCtxParams) context.Context {
	return context.WithValue(ctx, knKey{}, params)
}

// Log records the passed log message in the hosting application's log.
// The passed context must have been prepared with WithKnossosContext().
func Log(ctx context.Context, level LogLevel, message string, args ...interface{}) {
	params := ctx.Value(knKey{})
	if params == nil {
		panic("Invalid context provided. This is not a KnossosContext")
	}

	params.(KnossosCtxParams).LogCallback(level, message, args...)
}

// DispatchMessage delivers a progress message to the hosting application. This can be used to update the UI, generate
// log messages, etc. Knossos itself uses this for progress displays.
// The passed context must have been prepared with WithKnossosContext().
func DispatchMessage(ctx context.Context, event *client.ClientSentEvent) error {
	params := ctx.Value(knKey{})
	if params == nil {
		panic("Invalid context provided. This is not a KnossosContext")
	}

	return params.(KnossosCtxParams).MessageCallback(event)
}

// ResourcePath returns the path to the bundled resource files
func ResourcePath(ctx context.Context) string {
	params := ctx.Value(knKey{})
	if params == nil {
		panic("Invalid context provided. This is not a KnossosContext")
	}

	return params.(KnossosCtxParams).ResourcePath
}

// SettingsPath returns the path to the current settings directory (either the current portable directory or the
// default settings folder inside the user's profile)
func SettingsPath(ctx context.Context) string {
	params := ctx.Value(knKey{})
	if params == nil {
		panic("Invalid context provided. This is not a KnossosContext")
	}

	return params.(KnossosCtxParams).SettingsPath
}

// UpdateTask updates the state of a task started by the UI (JavaScript). `ref` contains the task ID and is used by the
// UI to find the corresponding UI elements.
// Usually, you won't call this function directly and instead use either SetProgress() or TaskLog().
func UpdateTask(ctx context.Context, ref uint32, msg interface{}) error {
	wrapped := &client.ClientSentEvent{Ref: ref}

	switch m := msg.(type) {
	case *client.ProgressMessage:
		wrapped.Payload = &client.ClientSentEvent_Progress{
			Progress: m,
		}
	case *client.LogMessage:
		wrapped.Payload = &client.ClientSentEvent_Message{
			Message: m,
		}
	}

	return DispatchMessage(ctx, wrapped)
}

// SetProgress updates the progress of the passed task (ref is the task ID)
func SetProgress(ctx context.Context, ref uint32, progress float32, description string) {
	err := UpdateTask(ctx, ref, &client.ProgressMessage{
		Progress:      progress,
		Description:   description,
		Error:         false,
		Indeterminate: false,
	})
	if err != nil {
		Log(ctx, LogError, "Error in SetProgres(%d): %+v", ref, err)
	}
}

// TaskLog appends the passed log message to the given task (ref is the task ID)
func TaskLog(ctx context.Context, ref uint32, level client.LogMessage_LogLevel, msg string, args ...interface{}) {
	var sender string
	_, file, line, ok := runtime.Caller(1)
	if ok {
		pos := strings.Index(file, "/packages/")
		if pos > -1 {
			file = file[pos+10:]
		}

		sender = fmt.Sprintf("%s:%d", file, line)
	} else {
		sender = "unknown"
	}

	composedMsg := fmt.Sprintf(msg, args...)
	Log(ctx, LogInfo, "Task [%d]: %s", ref, composedMsg)
	if ref > 0 {
		err := UpdateTask(ctx, ref, &client.LogMessage{
			Level:   level,
			Message: composedMsg,
			Sender:  sender,
		})
		if err != nil {
			Log(ctx, LogError, "Error in TaskLog(%d): %+v", ref, err)
		}
	}
}

// ProgressCopier copies all available data from input to output while reporting the current progress and speed to the
// given task (ref is the task ID). It returns the speed in bytes / s on success or an error.
func ProgressCopier(ctx context.Context, stepInfo TaskStep, length int64, input io.Reader, output io.Writer) (int, error) {
	pos := 0
	lastPos := 0
	buffer := make([]byte, 4096)
	step := (stepInfo.To - float32(stepInfo.From)) / float32(length)
	lastUpdate := time.Now()
	interval := time.Millisecond * 300
	tracker := NewSpeedTracker()
	start := time.Now()

	for {
		read, err := input.Read(buffer)
		if err != nil {
			if err == io.EOF {
				SetProgress(ctx, stepInfo.Ref, stepInfo.To, stepInfo.Description)
				passedSecs := int(time.Since(start).Seconds())
				if passedSecs == 0 {
					return 0, nil
				}
				return pos / passedSecs, nil
			}
			return 0, eris.Wrap(err, "failed to read")
		}
		_, err = output.Write(buffer[:read])
		if err != nil {
			return 0, eris.Wrap(err, "failed to write")
		}

		pos += read
		if time.Since(lastUpdate) > interval {
			lastUpdate = time.Now()

			tracker.Track(pos - lastPos)
			lastPos = pos

			msg := fmt.Sprintf("%s %s/s", stepInfo.Description, FormatBytes(tracker.GetSpeed()))
			SetProgress(ctx, stepInfo.Ref, stepInfo.From+step*float32(pos), msg)
		}
	}
}
