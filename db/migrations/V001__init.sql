CREATE TABLE users (
	id integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	username text NOT NULL,
	password bytea NOT NULL,
	email text NOT NULL,
	reset_token text NOT NULL,
	role smallint NOT NULL
);

CREATE INDEX users_username_idx ON users (username);

CREATE TABLE mods (
	aid integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	modid text NOT NULL UNIQUE,
	title text NOT NULL,
	type smallint NOT NULL
);

CREATE INDEX mods_modid_idx ON mods (modid);
CREATE INDEX mods_type_idx ON mods (type);

CREATE TABLE files (
	id integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	storage_key text NOT NULL UNIQUE,
	filesize integer NOT NULL,
	public boolean NOT NULL,
    external text[] NULL,
	owner integer NOT NULL REFERENCES users (id)
);

CREATE TABLE mod_team_members (
	mod_aid integer NOT NULL REFERENCES mods (aid) DEFERRABLE,
	"user" integer NOT NULL REFERENCES users (id),
	role smallint NOT NULL,
	UNIQUE (mod_aid, "user")
);

CREATE INDEX mod_team_members_mod_aid_idx ON mod_team_members (mod_aid);
CREATE INDEX mod_team_members_user_idx ON mod_team_members ("user");

CREATE TABLE mod_releases (
	id integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	mod_aid integer NOT NULL REFERENCES mods (aid) DEFERRABLE,
	version text NOT NULL,
	stability smallint NOT NULL,
	description text NOT NULL,
	teaser integer REFERENCES files (id) DEFAULT NULL,
	banner integer REFERENCES files (id) DEFAULT NULL,
	release_thread text NOT NULL,
	screenshots integer[] NOT NULL,
	videos text[] NOT NULL,
	released timestamp with time zone DEFAULT NULL,
	updated timestamp with time zone DEFAULT NULL,
	notes text NOT NULL,
	cmdline text NOT NULL,
	UNIQUE (mod_aid, version)
);

CREATE INDEX mod_releases_mod_aid ON mod_releases (mod_aid);
CREATE INDEX mod_releases_version ON mod_releases (version);

CREATE TABLE mod_packages (
	id integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	release_id integer NOT NULL REFERENCES mod_releases (id) DEFERRABLE,
	name text NOT NULL,
	folder text NOT NULL,
	notes text NOT NULL,
	type smallint NOT NULL,
	cpu_specs text[] NOT NULL,
	knossos_vp boolean NOT NULL,
	UNIQUE (release_id, name)
);

CREATE INDEX mod_packages_release_id_idx ON mod_packages (release_id);

CREATE TABLE mod_package_dependencies (
	id integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	package_id integer NOT NULL REFERENCES mod_packages (id) DEFERRABLE,
	modid text NOT NULL REFERENCES mods (modid) DEFERRABLE,
	version text NOT NULL,
	packages text[] NOT NULL
);

CREATE INDEX mod_package_dependencies_package_id_idx ON mod_package_dependencies (package_id);

CREATE TABLE mod_package_archives (
	id integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	package_id integer NOT NULL REFERENCES mod_packages (id) DEFERRABLE,
	label text NOT NULL,
	destination text NOT NULL,
	checksum_algo text NOT NULL,
	checksum_digest bytea NOT NULL,
	file_id integer NOT NULL REFERENCES files (id)
);

CREATE INDEX mod_package_archives_package_id_idx ON mod_package_archives (package_id);

CREATE TABLE mod_package_files (
	id integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	package_id integer NOT NULL REFERENCES mod_packages (id) DEFERRABLE,
	path text NOT NULL,
	archive text NOT NULL,
	archive_path text NOT NULL,
	checksum_algo text NOT NULL,
	checksum_digest bytea NOT NULL
);

CREATE INDEX mod_package_files_package_id_idx ON mod_package_files (package_id);

CREATE TABLE mod_package_executables (
	id integer NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	package_id integer NOT NULL REFERENCES mod_packages (id) DEFERRABLE,
	path text NOT NULL,
	label text NOT NULL,
	priority smallint NOT NULL,
	debug boolean NOT NULL
);

CREATE INDEX mod_package_executables_package_id_idx ON mod_package_executables (package_id);
