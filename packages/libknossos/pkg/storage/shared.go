package storage

import (
	"bytes"
	"context"
	"path/filepath"

	"github.com/dgraph-io/badger/v3"
	"github.com/ngld/knossos/packages/libknossos/pkg/api"
)

var (
	db            *badger.DB
	knownPrefixes = [][]byte{
		[]byte("settings"),
		[]byte("local_mod#"),
		[]byte("local_modindex"),
	}
)

func Open(ctx context.Context) error {
	var err error

	dbPath := filepath.Join(api.SettingsPath(ctx), "state.db")
	db, err = badger.Open(
		badger.DefaultOptions(dbPath).
			// an empty db takes 2 * log file size so set this to a very low
			// value to avoid wasting disk space
			WithValueLogFileSize(2 << 20). // 2 MiB
			WithLogger(KnBadgerLogger{ctx: ctx}),
	)
	return err
}

func Clean(ctx context.Context) error {
	err := db.Update(func(txn *badger.Txn) error {
		iter := txn.NewIterator(badger.IteratorOptions{})
		for iter.Rewind(); iter.Valid(); iter.Next() {
			key := iter.Item().Key()
			ok := false
			for _, prefix := range knownPrefixes {
				if bytes.HasPrefix(key, prefix) {
					ok = true
					break
				}
			}

			if !ok {
				api.Log(ctx, api.LogInfo, "Purging key %s", key)
				err := txn.Delete(key)
				if err != nil {
					return err
				}
			}
		}

		return nil
	})
	if err != nil {
		return err
	}

	return db.Flatten(4)
}

func Close(ctx context.Context) {
	db.Close()
	db = nil
}

type KnBadgerLogger struct {
	badger.Logger
	ctx context.Context
}

func (l KnBadgerLogger) Errorf(msg string, args ...interface{}) {
	api.Log(l.ctx, api.LogError, msg, args...)
}

func (l KnBadgerLogger) Warningf(msg string, args ...interface{}) {
	api.Log(l.ctx, api.LogWarn, msg, args...)
}

func (l KnBadgerLogger) Infof(msg string, args ...interface{}) {
	api.Log(l.ctx, api.LogInfo, msg, args...)
}

func (l KnBadgerLogger) Debugf(msg string, args ...interface{}) {
	api.Log(l.ctx, api.LogInfo, msg, args...)
}
