CREATE EXTENSION IF NOT EXISTS unaccent;

DROP TRIGGER IF EXISTS update_mods_auto_cols ON mods;
DROP FUNCTION IF EXISTS update_mods_auto_cols;
DROP FUNCTION IF EXISTS normalize_string;

ALTER TABLE mods DROP COLUMN IF EXISTS normalized_title;

CREATE FUNCTION normalize_string(input text) RETURNS text
    STRICT IMMUTABLE LANGUAGE sql
    AS $$
    SELECT btrim(regexp_replace(lower(unaccent(input)), '\s+', ' '), ' ');
$$;

ALTER TABLE mods ADD COLUMN normalized_title text NOT NULL DEFAULT '';
CREATE INDEX mods_normalized_title_idx ON mods (normalized_title);

CREATE FUNCTION update_mods_auto_cols() RETURNS trigger
    LANGUAGE plpgsql AS $$
BEGIN
    NEW.normalized_title = normalize_string(NEW.title);
    RETURN NEW;
END
$$;

CREATE TRIGGER update_mods_auto_cols BEFORE INSERT OR UPDATE ON mods FOR EACH ROW EXECUTE FUNCTION update_mods_auto_cols();
UPDATE mods SET normalized_title = normalize_string(title);
