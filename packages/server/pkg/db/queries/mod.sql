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
INSERT INTO mod_releases (mod_aid, version, stability, description, teaser, banner, release_thread, screenshots,
        videos, released, updated, notes, cmdline, private)
    VALUES (pggen.arg('mod_aid'), pggen.arg('version'), pggen.arg('stability'), pggen.arg('description'), pggen.arg('teaser'),
        pggen.arg('banner'), pggen.arg('release_thread'), pggen.arg('screenshots'), pggen.arg('videos'),
        pggen.arg('released'), pggen.arg('updated'), pggen.arg('notes'), pggen.arg('cmdline'), pggen.arg('private'))
    RETURNING (id);
