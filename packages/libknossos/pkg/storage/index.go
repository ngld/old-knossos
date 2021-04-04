package storage

import (
	"encoding/json"

	bolt "go.etcd.io/bbolt"
)

var indexBucket = []byte("_indexes")

type StringListSorter func(string, []string) error

type StringListIndex struct {
	cache     map[string][]string
	batchMode bool
	sorter    StringListSorter
	Name      string
}

func NewStringListIndex(name string, sorter StringListSorter) *StringListIndex {
	return &StringListIndex{
		Name:   name,
		sorter: sorter,
	}
}

func (i *StringListIndex) StartBatch() {
	i.batchMode = true
}

func (i *StringListIndex) FinishBatch(tx *bolt.Tx) error {
	i.batchMode = false

	if i.sorter != nil {
		err := i.ForEach(tx, i.sorter)
		if err != nil {
			return err
		}
	}

	return i.Save(tx)
}

func (i *StringListIndex) getCache(tx *bolt.Tx) map[string][]string {
	if i.cache == nil {
		bucket := tx.Bucket(indexBucket)
		data := bucket.Get([]byte(i.Name))
		if data != nil {
			err := json.Unmarshal(data, &i.cache)
			if err != nil {
				i.Clear()
			}
		}
	}

	return i.cache
}

func (i *StringListIndex) Lookup(tx *bolt.Tx, key string) []string {
	return i.getCache(tx)[key]
}

func (i *StringListIndex) ForEach(tx *bolt.Tx, cb func(string, []string) error) error {
	items := i.getCache(tx)
	for k, v := range items {
		err := cb(k, v)
		if err != nil {
			return err
		}
	}

	return nil
}

func (i *StringListIndex) Clear() {
	i.cache = make(map[string][]string)
}

func (i *StringListIndex) BatchedAdd(key, value string) {
	if !i.batchMode {
		panic("BatchedAdd() called on an index that wasn't in batch mode!")
	}

	if i.cache == nil {
		i.Clear()
	}
	i.cache[key] = append(i.cache[key], value)
}

func (i *StringListIndex) Add(tx *bolt.Tx, key, value string) error {
	if i.cache == nil {
		i.Clear()
	}
	i.cache[key] = append(i.cache[key], value)

	if !i.batchMode {
		if i.sorter != nil {
			err := i.ForEach(tx, i.sorter)
			if err != nil {
				return err
			}
		}

		return i.Save(tx)
	}

	return nil
}

func (i *StringListIndex) Save(tx *bolt.Tx) error {
	if i.cache == nil {
		i.Clear()
	}

	encoded, err := json.Marshal(i.cache)
	if err != nil {
		return err
	}

	bucket := tx.Bucket(indexBucket)
	return bucket.Put([]byte(i.Name), encoded)
}
