-- name: CreateExternalFile :one
INSERT INTO files (storage_key, filesize, public, external, owner)
	VALUES (pggen.arg('storage_key'), pggen.arg('filesize'), pggen.arg('public'), pggen.arg('external'), pggen.arg('owner'))
	RETURNING (id);
