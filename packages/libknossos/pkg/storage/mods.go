package storage

import (
	"context"
	"encoding/json"
	"sort"
	"sync"

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

type ModProvider interface {
	GetVersionsForMod(string) ([]string, error)
	GetModMetadata(string, string) (*client.Release, error)
}

var (
	localModsBucket                           = []byte("local_mods")
	localModsIndexBucket                      = []byte("local_mods_index")
	localModVersionIndex                      = []byte("version")
	localModTypeIndex                         = []byte("type")
	userModSettingsBucket                     = []byte("user_mod_settings")
	cachedVersionIdx      map[string][]string = nil
	cachedVersionIdxLock                      = sync.Mutex{}
	updateVersionIdxLock                      = sync.Mutex{}
)

func GetLocalModKey(rel *client.Release) []byte {
	return []byte(rel.Modid + "#" + rel.Version)
}

func getVersionIndex(tx *bolt.Tx) (map[string][]string, error) {
	if cachedVersionIdx == nil {
		cachedVersionIdxLock.Lock()
		defer cachedVersionIdxLock.Unlock()

		if cachedVersionIdx != nil {
			return cachedVersionIdx, nil
		}

		encoded := tx.Bucket(localModsIndexBucket).Get(localModVersionIndex)
		if encoded == nil {
			return nil, nil
		}

		result := make(map[string][]string)
		err := json.Unmarshal(encoded, &result)
		if err != nil {
			return nil, err
		}

		cachedVersionIdx = result
	}

	return cachedVersionIdx, nil
}

func updateVersionIdx(tx *bolt.Tx, modid string, versions []string) error {
	updateVersionIdxLock.Lock()
	defer updateVersionIdxLock.Unlock()

	// Load the index if necessary
	if cachedVersionIdx == nil {
		getVersionIndex(tx)
	}

	cachedVersionIdx[modid] = versions
	encoded, err := json.Marshal(&cachedVersionIdx)
	if err != nil {
		return err
	}

	return tx.Bucket(localModsIndexBucket).Put(localModVersionIndex, encoded)
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

		// Clear indexes to make sure nothing uses them during the import since they'd be empty during the initial import.
		indexBucket := tx.Bucket(localModsIndexBucket)

		encoded, err := json.Marshal(&modIndex)
		if err != nil {
			return err
		}
		err = indexBucket.Put(localModVersionIndex, encoded)
		if err != nil {
			return err
		}

		encoded, err = json.Marshal(&typeIndex)
		if err != nil {
			return err
		}
		err = indexBucket.Put(localModTypeIndex, encoded)
		if err != nil {
			return err
		}

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

		encoded, err = json.Marshal(modIndex)
		if err != nil {
			return err
		}

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

func ImportUserSettings(ctx context.Context, callback func(context.Context, func(string, string, *client.UserSettings) error) error) error {
	return db.Update(func(tx *bolt.Tx) error {
		bucket := tx.Bucket(userModSettingsBucket)

		// Remove existing entries
		err := bucket.ForEach(func(k, _ []byte) error {
			return bucket.Delete(k)
		})
		if err != nil {
			return err
		}

		ctx = CtxWithTx(ctx, tx)

		return callback(ctx, func(modID, version string, us *client.UserSettings) error {
			encoded, err := proto.Marshal(us)
			if err != nil {
				return err
			}

			return bucket.Put([]byte(modID+"#"+version), encoded)
		})
	})
}

func SaveLocalMod(ctx context.Context, release *client.Release) error {
	tx := TxFromCtx(ctx)
	if tx == nil {
		return BatchUpdate(ctx, func(ctx context.Context) error {
			return SaveLocalMod(ctx, release)
		})
	}

	bucket := tx.Bucket(localModsBucket)
	versionIdx, err := getVersionIndex(tx)
	if err != nil {
		return err
	}

	versions, ok := versionIdx[release.Modid]
	isNew := false
	if ok {
		verPresent := false
		for _, ver := range versions {
			if ver == release.Version {
				verPresent = true
				break
			}
		}

		if !verPresent {
			isNew = true
		}
	} else {
		isNew = true

		// Since this is the first entry for this mod, we also have to update the type index
		indexBucket := tx.Bucket(localModsIndexBucket)
		data := indexBucket.Get(localModTypeIndex)

		var typeIndex modTypeIndex
		err = json.Unmarshal(data, &typeIndex)
		if err != nil {
			return eris.Wrap(err, "failed to decode local mod type index")
		}

		typeIndex[release.Type] = append(typeIndex[release.Type], release.Modid)
		data, err = json.Marshal(typeIndex)
		if err != nil {
			return eris.Wrap(err, "failed to re-encode type index")
		}

		err = indexBucket.Put(localModTypeIndex, data)
		if err != nil {
			return eris.Wrap(err, "failed to save mod type index")
		}
	}

	// Update the version index for new mods
	if isNew {
		parsedVersions := make([]*semver.Version, len(versions)+1)
		for idx, rawVer := range versions {
			ver, err := semver.NewVersion(rawVer)
			if err != nil {
				return eris.Wrapf(err, "failed to parse old version %s", ver)
			}
			parsedVersions[idx] = ver
		}

		newVer, err := semver.NewVersion(release.Version)
		if err != nil {
			return eris.Wrap(err, "failed to parse new version")
		}
		parsedVersions[len(versions)] = newVer

		sort.Sort(semver.Collection(parsedVersions))

		versions = make([]string, len(parsedVersions))
		for idx, pVer := range parsedVersions {
			versions[idx] = pVer.String()
		}

		updateVersionIdx(tx, release.Modid, versions)
	}

	// Finally, we can save the actual mod
	encoded, err := proto.Marshal(release)
	if err != nil {
		return eris.Wrap(err, "failed to encode release")
	}
	return bucket.Put([]byte(release.Modid+"#"+release.Version), encoded)
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
		for modID, versions := range versionIdx {
			item := bucket.Get([]byte(modID + "#" + versions[len(versions)-1]))
			if item == nil {
				return eris.Errorf("Failed to find mod %s from index", modID+"#"+versions[len(versions)-1])
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

func GetVersionsForMod(ctx context.Context, id string) ([]string, error) {
	var result []string
	err := db.View(func(tx *bolt.Tx) error {
		versionIdx, err := getVersionIndex(tx)
		if err != nil {
			return err
		}

		versions, ok := versionIdx[id]
		if !ok {
			return eris.Errorf("No versions found for mod %s", id)
		}

		result = versions
		return nil
	})
	if err != nil {
		return nil, err
	}

	return result, nil
}

type LocalMods struct{}

var _ ModProvider = (*LocalMods)(nil)

func (LocalMods) GetVersionsForMod(id string) ([]string, error) {
	return GetVersionsForMod(context.Background(), id)
}

func (LocalMods) GetModMetadata(id, version string) (*client.Release, error) {
	return GetMod(context.Background(), id, version)
}

func SaveUserSettingsForMod(ctx context.Context, id, version string, settings *client.UserSettings) error {
	return db.Update(func(tx *bolt.Tx) error {
		encoded, err := proto.Marshal(settings)
		if err != nil {
			return err
		}

		bucket := tx.Bucket(userModSettingsBucket)
		return bucket.Put([]byte(id+"#"+version), encoded)
	})
}

func GetUserSettingsForMod(ctx context.Context, id, version string) (*client.UserSettings, error) {
	result := new(client.UserSettings)
	err := db.View(func(tx *bolt.Tx) error {
		bucket := tx.Bucket(userModSettingsBucket)

		encoded := bucket.Get([]byte(id + "#" + version))
		if encoded != nil {
			return proto.Unmarshal(encoded, result)
		} else {
			return nil
		}
	})
	if err != nil {
		return nil, err
	}

	return result, nil
}
