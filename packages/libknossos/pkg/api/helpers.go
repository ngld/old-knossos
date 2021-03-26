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
	LogDebug LogLevel = iota + 1
	LogInfo
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

var clientLogLevelMap = map[LogLevel]client.LogMessage_LogLevel{
	LogDebug: client.LogMessage_DEBUG,
	LogInfo:  client.LogMessage_INFO,
	LogWarn:  client.LogMessage_WARNING,
	LogError: client.LogMessage_ERROR,
	LogFatal: client.LogMessage_FATAL,
}

// KnossosCtxParams acts as a container for important info stored in the context
type KnossosCtxParams struct {
	// LogCallback is a function that records the passed message in the host application's logging system
	LogCallback func(LogLevel, string, ...interface{})
	// MessageCallback receives progress and status messages which provide details for ongoing tasks
	MessageCallback func(*client.ClientSentEvent) error
	SettingsPath    string
	ResourcePath    string
}

// TaskCtxParams stores info related to the current task
type TaskCtxParams struct {
	Ref uint32
}

// TaskStep contains common step parameters to make function calls related to task steps simpler
type TaskStep struct {
	Description string
	From        float32
	To          float32
}

type (
	knKey      struct{}
	taskCtxKey struct{}
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

// WithTaskContext stores the passed task info in the context
func WithTaskContext(ctx context.Context, params TaskCtxParams) context.Context {
	return context.WithValue(ctx, taskCtxKey{}, &params)
}

// GetTaskContext retrieves the current task info from the passed context.
// If required is true and no info is available, the function panics. Otherwise, nil is returned.
func GetTaskContext(ctx context.Context, required bool) *TaskCtxParams {
	params := ctx.Value(taskCtxKey{})
	if params == nil {
		if required {
			panic("Invalid context provided. Expected TaskCtxParams but couldn't find any.")
		}
		return nil
	}

	return params.(*TaskCtxParams)
}

func logImpl(ctx context.Context, level LogLevel, message string, args ...interface{}) {
	params := ctx.Value(knKey{})
	if params == nil {
		panic("Invalid context provided. This is not a KnossosContext")
	}

	params.(KnossosCtxParams).LogCallback(level, message, args...)
}

// Log records the passed log message in the hosting application's log.
// The passed context must have been prepared with WithKnossosContext().
func Log(ctx context.Context, level LogLevel, message string, args ...interface{}) {
	if GetTaskContext(ctx, false) == nil {
		logImpl(ctx, level, message, args...)
	} else {
		TaskLog(ctx, clientLogLevelMap[level], message, args...)
	}
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
func UpdateTask(ctx context.Context, msg interface{}) error {
	ref := GetTaskContext(ctx, true).Ref
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
	case *client.TaskResult:
		wrapped.Payload = &client.ClientSentEvent_Result{
			Result: m,
		}
	}

	return DispatchMessage(ctx, wrapped)
}

// SetProgress updates the progress of the passed task (ref is the task ID)
func SetProgress(ctx context.Context, progress float32, description string) {
	err := UpdateTask(ctx, &client.ProgressMessage{
		Progress:      progress,
		Description:   description,
		Error:         false,
		Indeterminate: false,
	})
	if err != nil {
		ref := GetTaskContext(ctx, true).Ref
		Log(ctx, LogError, "Error in SetProgress(%d): %+v", ref, err)
	}
}

// TaskLog appends the passed log message to the given task (ref is the task ID)
func TaskLog(ctx context.Context, level client.LogMessage_LogLevel, msg string, args ...interface{}) {
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

	ref := GetTaskContext(ctx, true).Ref
	composedMsg := fmt.Sprintf(msg, args...)
	logImpl(ctx, LogInfo, "Task [%d]: %s", ref, composedMsg)
	if ref > 0 {
		err := UpdateTask(ctx, &client.LogMessage{
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
				SetProgress(ctx, stepInfo.To, stepInfo.Description)
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
			SetProgress(ctx, stepInfo.From+step*float32(pos), msg)
		}
	}
}

// RunTask updates the context with the necessary task info and handles errors as well as panics from the task.
func RunTask(ctx context.Context, ref uint32, task func(context.Context) error) {
	go func() {
		ctx = WithTaskContext(ctx, TaskCtxParams{Ref: ref})
		defer func() {
			err := recover()
			if err != nil {
				TaskLog(ctx, client.LogMessage_FATAL, "Failed with panic: %+v", err)
				UpdateTask(ctx, &client.TaskResult{
					Success: false,
					Error:   "Failed with panic",
				})
			}
		}()

		err := task(ctx)
		if err != nil {
			TaskLog(ctx, client.LogMessage_ERROR, "Failed with error: %s", eris.ToString(err, true))
			UpdateTask(ctx, &client.TaskResult{
				Success: false,
				Error:   err.Error(),
			})
		} else {
			UpdateTask(ctx, &client.TaskResult{
				Success: true,
			})
		}
	}()
}
