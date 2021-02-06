ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_unique_idx;
ALTER TABLE users DROP COLUMN IF EXISTS created_at;
ALTER TABLE users DROP COLUMN IF EXISTS validated;

ALTER TABLE users ADD CONSTRAINT users_username_unique_idx UNIQUE (username);
ALTER TABLE users ADD COLUMN created_at timestamp with time zone NOT NULL DEFAULT NOW();
ALTER TABLE users ADD COLUMN validated boolean NOT NULL DEFAULT false;
