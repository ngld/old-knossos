package server

import (
	"net/http"
	"time"

	"github.com/gorilla/mux"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/unrolled/secure"

	"github.com/ngld/knossos/packages/api/api"
	"github.com/ngld/knossos/packages/server/pkg/auth"
	"github.com/ngld/knossos/packages/server/pkg/config"
	"github.com/ngld/knossos/packages/server/pkg/db/queries"
	"github.com/ngld/knossos/packages/server/pkg/nblog"
)

func startMux(pool *pgxpool.Pool, q *queries.DBQuerier, cfg *config.Config) error {
	server := api.NewNebulaServer(nebula{
		Pool: pool,
		Q:    q,
		Cfg:  cfg,
	})

	r := mux.NewRouter()
	r.PathPrefix(server.PathPrefix()).Handler(server)

	sm := secure.New(secure.Options{
		// TODO: Figure out how to only enable in production
		// SSLRedirect: true,
		IsDevelopment:      true,
		BrowserXssFilter:   true,
		ContentTypeNosniff: true,
		FrameDeny:          true,
	})

	muxServer := http.Server{
		Handler:      sm.Handler(auth.MakeAuthMiddleware(nblog.MakeLogMiddleware(r))),
		Addr:         cfg.HTTP.Address,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
	}

	return muxServer.ListenAndServe()
}
