package storage

import (
	"context"

	"github.com/ngld/knossos/packages/api/client"
	"github.com/rotisserie/eris"
	"go.etcd.io/bbolt"
	"google.golang.org/protobuf/proto"
)

var fileBucket = []byte("files")

func ImportFile(ctx context.Context, ref *client.FileRef) error {
	tx := TxFromCtx(ctx)
	if tx == nil {
		return db.Update(func(tx *bbolt.Tx) error {
			return ImportFile(CtxWithTx(ctx, tx), ref)
		})
	}

	encoded, err := proto.Marshal(ref)
	if err != nil {
		return err
	}

	return tx.Bucket(fileBucket).Put([]byte(ref.Fileid), encoded)
}

func GetFile(ctx context.Context, id string) (*client.FileRef, error) {
	tx := TxFromCtx(ctx)
	if tx == nil {
		var result *client.FileRef
		var err error
		err = db.View(func(tx *bbolt.Tx) error {
			result, err = GetFile(CtxWithTx(ctx, tx), id)
			return err
		})
		if err != nil {
			return nil, err
		}
		return result, nil
	}

	ref := new(client.FileRef)
	item := tx.Bucket(fileBucket).Get([]byte(id))

	if item == nil {
		return nil, eris.New("file not found")
	}

	err := proto.Unmarshal(item, ref)
	if err != nil {
		return nil, err
	}

	return ref, nil
}
