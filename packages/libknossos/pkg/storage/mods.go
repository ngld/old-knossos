package storage

import (
	"context"
	"encoding/json"
	"strings"

	"github.com/Masterminds/semver/v3"
	"github.com/dgraph-io/badger/v3"
	"github.com/ngld/knossos/packages/api/client"
	"github.com/ngld/knossos/packages/libknossos/pkg/api"
)

type KnDep struct {
	ID       string
	Version  string
	Packages []string
}

type KnExe struct {
	File       string
	Label      string
	Properties struct {
		X64  bool
		SSE2 bool
		AVX  bool
		AVX2 bool
	}
}

type KnChecksum [2]string

type KnArchive struct {
	Checksum KnChecksum
	Filename string
	Dest     string
	URLs     []string
	FileSize int
}

type KnFile struct {
	Filename string
	Archive  string
	OrigName string
	Checksum KnChecksum
}

type KnPackage struct {
	Name         string
	Notes        string
	Status       string
	Environment  string
	Folder       string
	Dependencies []KnDep
	Executables  []KnExe
	Files        []KnArchive
	Filelist     []KnFile
	IsVp         bool
}

type KnMod struct {
	LocalPath     string
	Title         string
	Version       string
	Stability     string
	Description   string
	Logo          string
	Tile          string
	Banner        string
	ReleaseThread string `json:"release_thread"`
	Type          string
	ID            string
	Notes         string
	Folder        string
	FirstRelease  string `json:"first_release"`
	LastUpdate    string `json:"last_update"`
	Cmdline       string
	ModFlag       []string `json:"mod_flag"`
	Screenshots   []string
	Packages      []KnPackage
	Videos        []string
}

type KnModIndex map[string][]string

func ImportMods(ctx context.Context, callback func(func(*KnMod) error) error) error {
	return db.Update(func(txn *badger.Txn) error {
		index := make(KnModIndex)
		err := callback(func(km *KnMod) error {
			encoded, err := json.Marshal(km)
			if err != nil {
				return err
			}

			err = txn.Set([]byte("local_mod#"+km.ID+"#"+km.Version), encoded)
			if err != nil {
				return err
			}
			index[km.ID] = append(index[km.ID], km.Version)

			return nil
		})
		if err != nil {
			return err
		}

		encoded, err := json.Marshal(index)
		if err != nil {
			return err
		}

		return txn.Set([]byte("local_modindex"), encoded)
	})
}

func GetSimpleLocalModList(ctx context.Context, taskRef uint32) ([]*KnMod, error) {
	modVersions := make(map[string]*semver.Version)
	var result []*KnMod

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

		result = make([]*KnMod, 0, len(modVersions))
		// Now retrieve the actual metadata
		for modID, version := range modVersions {
			item, err := txn.Get([]byte("local_mod#" + modID + "#" + version.String()))
			if err != nil {
				return err
			}

			meta := new(KnMod)
			err = item.Value(func(val []byte) error {
				return json.Unmarshal(val, meta)
			})
			if err != nil {
				return err
			}

			// Remove the package metadata avoid wasting memory
			meta.Packages = make([]KnPackage, 0)
			result = append(result, meta)
		}

		return nil
	})
	if err != nil {
		return nil, err
	}

	return result, nil
}
