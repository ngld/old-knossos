-- name: CreateExternalFile :one
INSERT INTO files (storage_key, filesize, public, external, owner)
	VALUES (pggen.arg('storage_key'), pggen.arg('filesize'), pggen.arg('public'), pggen.arg('external'), pggen.arg('owner'))
	RETURNING (id);

-- name: GetPublicFileByID :one
SELECT storage_key, external FROM files WHERE public = true AND id = pggen.arg('id') LIMIT 1;
