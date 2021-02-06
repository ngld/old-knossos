package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"strconv"
	"strings"

	"github.com/jackc/pgx"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/rotisserie/eris"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"github.com/ngld/knossos/packages/server/pkg/config"
	"github.com/ngld/knossos/packages/server/pkg/db/queries"
	"github.com/ngld/knossos/packages/server/pkg/importer"
	"github.com/ngld/knossos/packages/server/pkg/nblog"
)

func main() {
	cfg, loader := config.Loader()
	// flags := loader.Flags()

	if err := loader.Load(); err != nil {
		if strings.Contains(err.Error(), "help requested") {
			os.Exit(3)
		}

		panic(err)
	}

	writer := zerolog.ConsoleWriter{Out: os.Stdout}
	writer.TimeFormat = "02.01.2006 15:04:05 MST"
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

	log.Logger = log.Output(writer)

	zerolog.ErrorStackMarshaler = func(err error) interface{} {
		return eris.ToString(err, true)
	}

	if err := cfg.Validate(); err != nil {
		log.Fatal().Err(err).Msg("Failed to parse config")
	}

	zerolog.SetGlobalLevel(cfg.LogLevel())

	log.Logger = log.Logger.With().Caller().Stack().Logger()
	log.Info().Msg("Finished parsing configuration; loading data")

	inFile, err := os.Open("repo.json")
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to open repo.json")
	}
	defer inFile.Close()

	jsonStr, err := ioutil.ReadAll(inFile)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to read repo.json")
	}

	data := importer.KnStruct{}
	err = json.Unmarshal(jsonStr, &data)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to parse repo.json")
	}

	dbConfig, err := pgxpool.ParseConfig(cfg.Database)
	if err != nil {
		return err
	}

	dbConfig.ConnConfig.Logger = nblog.PgxLogger{}
	dbConfig.ConnConfig.LogLevel = pgx.LogLevelDebug
	pool, err := pgxpool.ConnectConfig(context.Background(), dbConfig)
	if err != nil {
		return err
	}

	q := queries.NewQuerier(pool)

	count := len(data.Mods)
	aidCache := map[string]int{}
	for i, mod := range data.Mods {
		log.Info().Msgf("Mod %4d of %d", i, count)

		aid, ok := aidCache[mod.ID]
		if !ok {
			res := nil
		}
	}
}
