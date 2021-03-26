package storage

import (
	"context"
	"encoding/json"
	"sort"

	"github.com/Masterminds/semver/v3"
	"github.com/ngld/knossos/packages/api/client"
	"github.com/rotisserie/eris"
	bolt "go.etcd.io/bbolt"
	"google.golang.org/protobuf/proto"
)

type (
	stringIndex  map[string][]string
	modTypeIndex map[client.ModType][]string
)

var (
	localModsBucket      = []byte("local_mods")
	localModsIndexBucket = []byte("local_mods_index")
	localModVersionIndex = []byte("version")
	localModTypeIndex    = []byte("type")
)

func GetLocalModKey(rel *client.Release) []byte {
	return []byte(rel.Modid + "#" + rel.Version)
}

func getVersionIndex(tx *bolt.Tx) (map[string][]string, error) {
	encoded := tx.Bucket(localModsIndexBucket).Get(localModVersionIndex)
	if encoded == nil {
		return nil, nil
	}

	result := make(map[string][]string)
	err := json.Unmarshal(encoded, &result)
	if err != nil {
		return nil, err
	}

	return result, nil
}

func ImportMods(ctx context.Context, callback func(context.Context, func(*client.Release) error) error) error {
	return db.Update(func(tx *bolt.Tx) error {
		bucket := tx.Bucket(localModsBucket)

		// Remove existing entries
		err := bucket.ForEach(func(k, _ []byte) error {
			return bucket.Delete(k)
		})
		if err != nil {
			return err
		}

		modIndex := make(stringIndex)
		typeIndex := make(modTypeIndex)

		ctx = CtxWithTx(ctx, tx)

		// Call the actual import function
		err = callback(ctx, func(rel *client.Release) error {
			encoded, err := proto.Marshal(rel)
			if err != nil {
				return err
			}

			err = bucket.Put(GetLocalModKey(rel), encoded)
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

		// Sort the version index
		for _, versions := range modIndex {
			parsed := make(semver.Collection, len(versions))
			for idx, raw := range versions {
				parsed[idx], err = semver.StrictNewVersion(raw)
				if err != nil {
					return err
				}
			}

			sort.Sort(parsed)
			for idx, version := range parsed {
				versions[idx] = version.String()
			}
		}

		encoded, err := json.Marshal(modIndex)
		if err != nil {
			return err
		}

		indexBucket := tx.Bucket(localModsIndexBucket)
		err = indexBucket.Put(localModVersionIndex, encoded)
		if err != nil {
			return err
		}

		encoded, err = json.Marshal(typeIndex)
		if err != nil {
			return err
		}

		return indexBucket.Put(localModTypeIndex, encoded)
	})
}

func GetLocalMods(ctx context.Context, taskRef uint32) ([]*client.Release, error) {
	var result []*client.Release

	err := db.View(func(tx *bolt.Tx) error {
		// Retrieve IDs and the latest version for all known local mods
		bucket := tx.Bucket(localModsBucket)
		versionIdx, err := getVersionIndex(tx)
		if err != nil {
			return err
		}

		result = make([]*client.Release, 0, len(versionIdx))
		for modId, versions := range versionIdx {
			item := bucket.Get([]byte(modId + "#" + versions[len(versions)-1]))
			if item == nil {
				return eris.Errorf("Failed to find mod %s from index", modId+"#"+versions[len(versions)-1])
			}

			meta := new(client.Release)
			err = proto.Unmarshal(item, meta)
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
	err := db.View(func(tx *bolt.Tx) error {
		item := tx.Bucket(localModsBucket).Get([]byte(id + "#" + version))
		if item == nil {
			return eris.New("mod not found")
		}

		return proto.Unmarshal(item, mod)
	})
	if err != nil {
		return nil, err
	}
	return mod, nil
}
