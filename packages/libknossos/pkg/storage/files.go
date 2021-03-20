package storage

import (
	"context"

	"github.com/dgraph-io/badger/v3"
	"github.com/ngld/knossos/packages/api/client"
	"google.golang.org/protobuf/proto"
)

var filePrefix = "file#"

func ImportFile(ctx context.Context, ref *client.FileRef) error {
	return db.Update(func(txn *badger.Txn) error {
		encoded, err := proto.Marshal(ref)
		if err != nil {
			return err
		}

		return txn.Set([]byte(filePrefix+ref.Fileid), encoded)
	})
}

func GetFile(ctx context.Context, id string) (*client.FileRef, error) {
	ref := new(client.FileRef)
	err := db.View(func(txn *badger.Txn) error {
		item, err := txn.Get([]byte(filePrefix + id))
		if err != nil {
			return err
		}

		return item.Value(func(val []byte) error {
			return proto.Unmarshal(val, ref)
		})
	})
	if err != nil {
		return nil, err
	}

	return ref, nil
}
