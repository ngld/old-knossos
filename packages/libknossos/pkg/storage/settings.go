package storage

import (
	"context"
	"encoding/json"

	"github.com/dgraph-io/badger/v3"
	"github.com/ngld/knossos/packages/api/client"
	"github.com/rotisserie/eris"
)

var settingsKey = []byte("settings")

func GetSettings(ctx context.Context) (*client.Settings, error) {
	settings := new(client.Settings)
	err := db.View(func(txn *badger.Txn) error {
		item, err := txn.Get(settingsKey)
		if err != nil {
			if eris.Is(err, badger.ErrKeyNotFound) {
				return nil
			}
			return err
		}

		return item.Value(func(val []byte) error {
			return json.Unmarshal(val, &settings)
		})
	})
	return settings, err
}

func SaveSettings(ctx context.Context, settings *client.Settings) error {
	encoded, err := json.Marshal(settings)
	if err != nil {
		return err
	}

	return db.Update(func(txn *badger.Txn) error {
		return txn.Set(settingsKey, encoded)
	})
}
