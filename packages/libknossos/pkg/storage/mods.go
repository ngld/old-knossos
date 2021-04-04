package storage

import (
	"context"
	"sort"
	"sync"

	"github.com/ngld/knossos/packages/api/client"
	"github.com/rotisserie/eris"
	bolt "go.etcd.io/bbolt"
	"google.golang.org/protobuf/proto"
)

type ModProvider interface {
	GetVersionsForMod(string) ([]string, error)
	GetModMetadata(string, string) (*client.Release, error)
}

var (
	localModsBucket       = []byte("local_mods")
	userModSettingsBucket = []byte("user_mod_settings")
	localVersionIdx       = NewStringListIndex("local_mod_versions", modVersionSorter)
	// TODO maybe add a Uint8ListIndex?
	localTypeIdx = NewStringListIndex("local_mod_types", nil)
	importMutex  = sync.Mutex{}
)

func modVersionSorter(_ string, versions []string) error {
	vcoll, err := NewStringVersionCollection(versions)
	if err != nil {
		return err
	}

	sort.Sort(vcoll)
	return nil
}

func ImportMods(ctx context.Context, callback func(context.Context, func(*client.Release) error) error) error {
	importMutex.Lock()
	defer importMutex.Unlock()

	return db.Update(func(tx *bolt.Tx) error {
		bucket := tx.Bucket(localModsBucket)

		// Remove existing entries
		err := bucket.ForEach(func(k, _ []byte) error {
			return bucket.Delete(k)
		})
		if err != nil {
			return err
		}

		// Clear indexes to make sure nothing uses them during the import since they'd be empty during the initial import.
		localVersionIdx.Clear()
		localTypeIdx.Clear()

		localVersionIdx.StartBatch()
		localTypeIdx.StartBatch()

		ctx = CtxWithTx(ctx, tx)

		// Call the actual import function
		err = callback(ctx, func(rel *client.Release) error {
			encoded, err := proto.Marshal(rel)
			if err != nil {
				return err
			}

			err = bucket.Put([]byte(rel.Modid+"#"+rel.Version), encoded)
			if err != nil {
				return err
			}

			if len(localVersionIdx.Lookup(tx, rel.Modid)) < 1 {
				// This is the first time we process this mod

				// Add this mod to our type index
				localTypeIdx.BatchedAdd(string(rel.Type), rel.Modid)
			}

			localVersionIdx.BatchedAdd(rel.Modid, rel.Version)
			return nil
		})
		if err != nil {
			return err
		}

		err = localVersionIdx.FinishBatch(tx)
		if err != nil {
			return err
		}

		return localTypeIdx.FinishBatch(tx)
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

	importMutex.Lock()
	defer importMutex.Unlock()

	bucket := tx.Bucket(localModsBucket)
	versions := localVersionIdx.Lookup(tx, release.Modid)

	isNew := false
	if len(versions) > 0 {
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
		err := localTypeIdx.Add(tx, string(release.Type), release.Modid)
		if err != nil {
			return err
		}
	}

	// Update the version index for new mods
	if isNew {
		err := localVersionIdx.Add(tx, release.Modid, release.Version)
		if err != nil {
			return err
		}
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
		result = make([]*client.Release, 0)

		localVersionIdx.ForEach(tx, func(modID string, versions []string) error {
			item := bucket.Get([]byte(modID + "#" + versions[len(versions)-1]))
			if item == nil {
				return eris.Errorf("Failed to find mod %s from index", modID+"#"+versions[len(versions)-1])
			}

			meta := new(client.Release)
			err := proto.Unmarshal(item, meta)
			if err != nil {
				return err
			}

			result = append(result, meta)
			return nil
		})

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
		result = localVersionIdx.Lookup(tx, id)
		return nil
	})
	if err != nil {
		return nil, err
	}

	if len(result) < 1 {
		return nil, eris.Errorf("No versions found for mod %s", id)
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
