package buildsys

import (
	"context"

	"github.com/rs/zerolog"
)

type logKey struct{}

func log(ctx context.Context) *zerolog.Logger {
	logger := ctx.Value(logKey{})
	if logger == nil {
		panic("Logger is missing in context!")
	}

	return logger.(*zerolog.Logger)
}

// WithLogger attaches the given logger to the context
func WithLogger(ctx context.Context, logger *zerolog.Logger) context.Context {
	return context.WithValue(ctx, logKey{}, logger)
}
