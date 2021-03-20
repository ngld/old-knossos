package storage

import (
	"context"
	"encoding/json"
	"strings"

	"github.com/Masterminds/semver/v3"
	"github.com/dgraph-io/badger/v3"
	"github.com/ngld/knossos/packages/api/client"
	"github.com/ngld/knossos/packages/libknossos/pkg/api"
	"google.golang.org/protobuf/proto"
)

type (
	stringIndex  map[string][]string
	modTypeIndex map[client.ModType][]string
)

var (
	localModIndexKey     = []byte("local_modindex")
	localModTypeIndexKey = []byte("local_modtypeindex")
)

func GetLocalModKey(rel *client.Release) []byte {
	return []byte("local_mod#" + rel.Modid + "#" + rel.Version)
}

func ImportMods(ctx context.Context, callback func(func(*client.Release) error) error) error {
	return db.Update(func(txn *badger.Txn) error {
		// Remove existing entries
		iter := txn.NewIterator(badger.IteratorOptions{
			Prefix: []byte("local_mod#"),
		})
		defer iter.Close()
		for iter.Rewind(); iter.Valid(); iter.Next() {
			err := txn.Delete(iter.Item().Key())
			if err != nil {
				return err
			}
		}
		iter.Close()

		modIndex := make(stringIndex)
		typeIndex := make(modTypeIndex)
		// Call the actual import function
		err := callback(func(rel *client.Release) error {
			encoded, err := proto.Marshal(rel)
			if err != nil {
				return err
			}

			err = txn.Set(GetLocalModKey(rel), encoded)
			if err != nil {
				return err
			}

			_, found := modIndex[rel.Modid]
			if !found {
				// This is the first time we process this mod

				// Add this mod to our type index
				typeIndex[rel.Type] = append(typeIndex[rel.Type], rel.Modid)
			}

			modIndex[rel.Modid] = append(modIndex[rel.Modid], rel.Version)

			return nil
		})
		if err != nil {
			return err
		}

		encoded, err := json.Marshal(modIndex)
		if err != nil {
			return err
		}

		err = txn.Set(localModIndexKey, encoded)
		if err != nil {
			return err
		}

		encoded, err = json.Marshal(typeIndex)
		if err != nil {
			return err
		}

		return txn.Set(localModTypeIndexKey, encoded)
	})
}

func GetLocalMods(ctx context.Context, taskRef uint32) ([]*client.Release, error) {
	modVersions := make(map[string]*semver.Version)
	var result []*client.Release

	err := db.View(func(txn *badger.Txn) error {
		// Retrieve IDs and the latest version for all known local mods
		iter := txn.NewIterator(badger.IteratorOptions{
			Prefix: []byte("local_mod#"),
		})
		defer iter.Close()
		for iter.Rewind(); iter.Valid(); iter.Next() {
			parts := strings.Split(string(iter.Item().Key()), "#")
			if len(parts) != 3 {
				api.TaskLog(ctx, taskRef, client.LogMessage_ERROR, "Skipping invalid key %s", iter.Item().Key())
				continue
			}

			version, err := semver.StrictNewVersion(parts[2])
			if err != nil {
				api.TaskLog(ctx, taskRef, client.LogMessage_ERROR,
					"Skipping invalid version %s for %s: %+v", parts[2], parts[1], err)
			}

			prevVersion, ok := modVersions[parts[1]]
			if !ok || version.Compare(prevVersion) > 0 {
				modVersions[parts[1]] = version
			}
		}

		result = make([]*client.Release, 0, len(modVersions))
		// Now retrieve the actual metadata
		for modID, version := range modVersions {
			item, err := txn.Get([]byte("local_mod#" + modID + "#" + version.String()))
			if err != nil {
				return err
			}

			meta := new(client.Release)
			err = item.Value(func(val []byte) error {
				return proto.Unmarshal(val, meta)
			})
			if err != nil {
				return err
			}

			result = append(result, meta)
		}

		return nil
	})
	if err != nil {
		return nil, err
	}

	return result, nil
}

func GetMod(ctx context.Context, id string, version string) (*client.Release, error) {
	mod := new(client.Release)
	err := db.View(func(txn *badger.Txn) error {
		item, err := txn.Get([]byte("local_mod#" + id + "#" + version))
		if err != nil {
			return err
		}

		return item.Value(func(val []byte) error {
			return proto.Unmarshal(val, mod)
		})
	})
	if err != nil {
		return nil, err
	}
	return mod, nil
}
