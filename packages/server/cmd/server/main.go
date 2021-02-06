package main

import (
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"github.com/rotisserie/eris"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"github.com/ngld/knossos/packages/server/pkg/config"
	"github.com/ngld/knossos/packages/server/pkg/server"
)

func getConsoleWriter(out io.Writer) zerolog.ConsoleWriter {
	writer := zerolog.ConsoleWriter{Out: out}
	writer.TimeFormat = "02.01.2006 15:04:05 MST"
	writer.PartsOrder = []string{
		zerolog.TimestampFieldName,
		"req",
		zerolog.LevelFieldName,
		zerolog.CallerFieldName,
		zerolog.MessageFieldName,
	}

	// writer.PartsExclude = []string{"req"}
	writer.FormatFieldValue = func(value interface{}) string {
		if value == nil {
			return "                "
		}

		str, ok := value.(string)
		if ok {
			if len(str) == 16 {
				// color request IDs in cyan  we have to guess based on the field content because we can't get
				// the current field name
				return fmt.Sprintf("\x1b[%dm%s\x1b[0m", 36, value)
			} else if strings.Contains(str, "\\n") && strings.Contains(str, "\\t") {
				// unquote values that contain line breaks and tabs because they're most likely stack traces
				str, err := strconv.Unquote(str)
				if err == nil {
					return str
				}
			}
		}

		return fmt.Sprintf("%s", value)
	}
	return writer
}

func main() {
	cfg, loader := config.Loader()
	// flags := loader.Flags()

	if err := loader.Load(); err != nil {
		if strings.Contains(err.Error(), "help requested") {
			os.Exit(3)
		}

		panic(err)
	}

	if cfg.Log.JSON {
		zerolog.ErrorStackMarshaler = func(err error) interface{} {
			return eris.ToJSON(err, true)
		}
	} else {
		log.Logger = log.Output(getConsoleWriter(os.Stderr))
		zerolog.ErrorStackMarshaler = func(err error) interface{} {
			return eris.ToString(err, true)
		}
	}

	if err := cfg.Validate(); err != nil {
		log.Fatal().Err(err).Msg("Failed to parse config")
	}

	zerolog.SetGlobalLevel(cfg.LogLevel())
	if cfg.Log.File != "" {
		var logFile io.Writer
		logFile, err := os.Create(cfg.Log.File)
		if err != nil {
			log.Fatal().Err(err).Msg("Failed to open log file")
		}

		if !cfg.Log.JSON {
			writer := getConsoleWriter(logFile)
			writer.NoColor = true
			logFile = writer
		}

		log.Logger = log.Output(logFile)
	}

	log.Logger = log.Logger.With().Caller().Stack().Logger()
	log.Info().Msg("Finished parsing configuration; starting server")

	err := server.StartServer(cfg)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to start server")
	}
}
