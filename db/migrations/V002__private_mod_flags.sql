ALTER TABLE mods DROP COLUMN IF EXISTS private;
ALTER TABLE mod_releases DROP COLUMN IF EXISTS private;

ALTER TABLE mods ADD COLUMN private boolean;
ALTER TABLE mod_releases ADD COLUMN private boolean;
