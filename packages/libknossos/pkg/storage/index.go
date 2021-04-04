package storage

import (
	"encoding/json"

	bolt "go.etcd.io/bbolt"
)

var indexBucket = []byte("_indexes")

type StringListSorter func(string, []string) error

type StringListIndex struct {
	cache     map[string][]string
	sorter    StringListSorter
	Name      string
	batchMode bool
}

func NewStringListIndex(name string, sorter StringListSorter) *StringListIndex {
	return &StringListIndex{
		Name:   name,
		sorter: sorter,
	}
}

func (i *StringListIndex) Open(tx *bolt.Tx) error {
	bucket := tx.Bucket(indexBucket)
	data := bucket.Get([]byte(i.Name))
	if data != nil {
		err := json.Unmarshal(data, &i.cache)
		if err != nil {
			return err
		}
	}

	return nil
}

func (i *StringListIndex) StartBatch() {
	i.batchMode = true
}

func (i *StringListIndex) FinishBatch(tx *bolt.Tx) error {
	i.batchMode = false

	if i.sorter != nil {
		err := i.ForEach(i.sorter)
		if err != nil {
			return err
		}
	}

	return i.Save(tx)
}

func (i *StringListIndex) Lookup(key string) []string {
	return i.cache[key]
}

func (i *StringListIndex) ForEach(cb func(string, []string) error) error {
	for k, v := range i.cache {
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
			err := i.ForEach(i.sorter)
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
