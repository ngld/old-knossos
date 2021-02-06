package nblog

import (
	"context"
	"net/http"

	"github.com/jackc/pgx/v4"
	"github.com/muyo/sno"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

type logPtr struct{}

func MakeLogMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(rw http.ResponseWriter, r *http.Request) {
		reqID := sno.New(0)
		logger := log.With().Str("req", reqID.String()).Logger()

		ctx := r.Context()
		ctx = context.WithValue(ctx, logPtr{}, &logger)
		r = r.WithContext(ctx)
		next.ServeHTTP(rw, r)
	})
}

// Log returns a zerolog Logger with additional context information (i.e. request ID)
func Log(ctx context.Context) *zerolog.Logger {
	logger := ctx.Value(logPtr{})
	if logger == nil {
		return &log.Logger
	}

	return logger.(*zerolog.Logger)
}

// PgxLogger implements pgx's logger interface
type PgxLogger struct{}

// Log is pgx-compatible wrapper around log()
func (PgxLogger) Log(ctx context.Context, level pgx.LogLevel, msg string, data map[string]interface{}) {
	var zlevel zerolog.Level
	switch level {
	case pgx.LogLevelNone:
		zlevel = zerolog.NoLevel
	case pgx.LogLevelError:
		zlevel = zerolog.ErrorLevel
	case pgx.LogLevelWarn:
		zlevel = zerolog.WarnLevel
	case pgx.LogLevelInfo:
		zlevel = zerolog.InfoLevel
	case pgx.LogLevelDebug:
		zlevel = zerolog.DebugLevel
	default:
		zlevel = zerolog.DebugLevel
	}

	Log(ctx).WithLevel(zlevel).Str("module", "pgx").Fields(data).Msg(msg)
}
