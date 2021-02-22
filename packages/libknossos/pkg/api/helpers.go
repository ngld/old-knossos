package api

import (
	"context"

	"github.com/ngld/knossos/packages/api/client"
)

// LogLevel indicates the severity of a log message
type LogLevel int

const (
	LogInfo LogLevel = iota + 1
	LogWarn
	LogError
	LogFatal
)

type (
	// LogCallback is a function that records the passed message in the host application's logging system
	LogCallback func(LogLevel, string, ...interface{})
	// MessageCallback receives progress and status messages which provide details for ongoing tasks
	MessageCallback func(*client.ClientSentEvent) error
)

type (
	logKey     struct{}
	messageKey struct{}
)

// WithKnossosContext stores the passed callbacks in the context which allows it to be used with Log() and DispatchMessage()
func WithKnossosContext(ctx context.Context, log LogCallback, message MessageCallback) context.Context {
	ctx = context.WithValue(ctx, logKey{}, log)
	ctx = context.WithValue(ctx, messageKey{}, message)
	return ctx
}

// Log records the passed log message in the hosting application's log.
// The passed context must have been prepared with WithKnossosContext().
func Log(ctx context.Context, level LogLevel, message string, args ...interface{}) {
	log := ctx.Value(logKey{})
	if log == nil {
		panic("Invalid context provided. This is not a KnossosContext")
	}

	log.(LogCallback)(level, message, args...)
}

// DispatchMessage delivers a progress message to the hosting application. This can be used to update the UI, generate
// log messages, etc. Knossos itself uses this for progress displays.
// The passed context must have been prepared with WithKnossosContext().
func DispatchMessage(ctx context.Context, event *client.ClientSentEvent) error {
	message := ctx.Value(messageKey{})
	if message == nil {
		panic("Invalid context provided. This is not a KnossosContext")
	}

	return message.(MessageCallback)(event)
}
