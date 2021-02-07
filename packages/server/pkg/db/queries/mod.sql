-- name: GetModDetailsByModID :one
SELECT title, type FROM mods WHERE modid = pggen.arg('modid') LIMIT 1;

-- name: GetModVisibility :one
SELECT private FROM mods WHERE modid = pggen.arg('modid') LIMIT 1;

-- name: GetReleaseVisibility :one
SELECT r.private AS release, m.private AS mod FROM mod_releases AS r LEFT JOIN mods AS m ON m.aid = r.mod_aid
    WHERE m.modid = pggen.arg('modid') AND r.version = pggen.arg('version') LIMIT 1;

-- name: GetModRoleByModID :one
SELECT t.role FROM mod_team_members AS t LEFT JOIN mods AS m ON m.aid = t.mod_aid
    WHERE m.modid = pggen.arg('modid') AND t.user = pggen.arg('user') LIMIT 1;

-- name: CreateMod :one
INSERT INTO mods (modid, title, type, private)
    VALUES (pggen.arg('modid'), pggen.arg('title'), pggen.arg('type'), pggen.arg('private'))
    RETURNING (aid);

-- name: CreateRelease :one
INSERT INTO mod_releases (mod_aid, version, stability, description, release_thread, screenshots,
        videos, released, updated, notes, cmdline, private, teaser, banner)
    VALUES (pggen.arg('mod_aid'), pggen.arg('version'), pggen.arg('stability'), pggen.arg('description'),
        pggen.arg('release_thread'), pggen.arg('screenshots'), pggen.arg('videos'), pggen.arg('released'),
        pggen.arg('updated'), pggen.arg('notes'), pggen.arg('cmdline'), pggen.arg('private'),
            -- workaround since pggen forces us to pass int32 which can't be null
            CASE WHEN pggen.arg('teaser') = 0 THEN null
                 ELSE pggen.arg('teaser')
            END,
            CASE WHEN pggen.arg('banner') = 0 THEN null
                 ELSE pggen.arg('banner')
            END
        )
    RETURNING (id);

-- name: CreatePackage :one
INSERT INTO mod_packages (release_id, name, folder, notes, type, cpu_specs, knossos_vp)
    VALUES (pggen.arg('release_id'), pggen.arg('name'), pggen.arg('folder'), pggen.arg('notes'), pggen.arg('type'),
        pggen.arg('cpu_specs'), pggen.arg('knossos_vp'))
    RETURNING (id);

-- name: CreatePackageDependency :one
INSERT INTO mod_package_dependencies (package_id, modid, version, packages)
    VALUES (pggen.arg('package_id'), pggen.arg('modid'), pggen.arg('version'), pggen.arg('packages'))
    RETURNING (id);

-- name: CreatePackageExecutable :one
INSERT INTO mod_package_executables (package_id, path, label, priority, debug)
    VALUES (pggen.arg('package_id'), pggen.arg('path'), pggen.arg('label'), pggen.arg('priority'), pggen.arg('debug'))
    RETURNING (id);

-- name: CreatePackageArchive :one
INSERT INTO mod_package_archives (package_id, label, destination, checksum_algo, checksum_digest, file_id)
    VALUES (pggen.arg('package_id'), pggen.arg('label'), pggen.arg('destination'), pggen.arg('checksum_algo'),
        pggen.arg('checksum_digest'), pggen.arg('file_id'))
    RETURNING (id);

-- name: CreatePackageFile :one
INSERT INTO mod_package_files (package_id, path, archive, archive_path, checksum_algo, checksum_digest)
    VALUES (pggen.arg('package_id'), pggen.arg('path'), pggen.arg('archive'), pggen.arg('archive_path'),
        pggen.arg('checksum_algo'), pggen.arg('checksum_digest'))
    RETURNING (id);
