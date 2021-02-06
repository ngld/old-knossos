package server

import (
	"context"

	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/rs/zerolog/log"

	"github.com/ngld/knossos/packages/server/pkg/auth"
	"github.com/ngld/knossos/packages/server/pkg/config"
	"github.com/ngld/knossos/packages/server/pkg/db/queries"
	"github.com/ngld/knossos/packages/server/pkg/mail"
	"github.com/ngld/knossos/packages/server/pkg/nblog"
)

type nebula struct {
	Pool *pgxpool.Pool
	Q    *queries.DBQuerier
	Cfg  *config.Config
}

// StartServer starts the integrated HTTP server
func StartServer(cfg *config.Config) error {
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

	auth.Init(q)
	err = mail.Init(cfg)
	if err != nil {
		return err
	}

	log.Info().Msgf("Listening on %s", cfg.HTTP.Address)
	return startMux(pool, q, cfg)
}
