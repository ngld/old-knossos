package db

//go:generate pggen gen go --postgres-connection "dbname=nebula" --query-glob ./queries/*.sql
