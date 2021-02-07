package db

//go:generate pggen gen go --postgres-connection "dbname=nebula" --query-glob ./queries/*.sql --go-type 'bytea=github.com/jackc/pgtype.Bytea' --go-type 'mod_releases.teaser=github.com/jackc/pgtype.Int' --go-type 'mod_releases.banner=github.com/jackc/pgtype.Banner'
