-- OrbVis SQLite schema — replaces alembic/versions/d57035487520_initial_schema.py.
-- Run idempotently at startup via sqlite3.executescript().
--
-- The CREATE TABLE statements mirror the SQLAlchemy models 1:1 so the on-disk
-- layout stays compatible with databases that were originally created by
-- alembic. _ensure_schema() additionally drops the alembic_version table when
-- it exists, so legacy installs converge on the same canonical state.

CREATE TABLE IF NOT EXISTS users (
    user_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 VARCHAR(100) NOT NULL UNIQUE,
    password             VARCHAR(255) NOT NULL,
    is_active            BOOLEAN      NOT NULL DEFAULT 1,
    is_admin             BOOLEAN      NOT NULL DEFAULT 0,
    must_change_password BOOLEAN      NOT NULL DEFAULT 0,
    theme                VARCHAR(10)  NOT NULL DEFAULT 'system',
    language             VARCHAR(10)  NOT NULL DEFAULT 'en'
);

CREATE INDEX IF NOT EXISTS ix_users_name ON users (name);

CREATE TABLE IF NOT EXISTS roles (
    role_id INTEGER      PRIMARY KEY AUTOINCREMENT,
    name    VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS permissions (
    perm_id INTEGER      PRIMARY KEY AUTOINCREMENT,
    mod     VARCHAR(100) NOT NULL,
    act     VARCHAR(100) NOT NULL,
    obj     VARCHAR(200) NOT NULL DEFAULT '*',
    CONSTRAINT uq_perm_triplet UNIQUE (mod, act, obj)
);

CREATE TABLE IF NOT EXISTS users2roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS roles2perms (
    role_id INTEGER NOT NULL,
    perm_id INTEGER NOT NULL,
    PRIMARY KEY (role_id, perm_id),
    FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE CASCADE,
    FOREIGN KEY (perm_id) REFERENCES permissions (perm_id) ON DELETE CASCADE
);
