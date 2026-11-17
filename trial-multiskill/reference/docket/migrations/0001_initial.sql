-- 0001: tenants, users, sessions, documents, shares.
-- Forward-only: never edit an applied migration; add a new numbered file instead.

CREATE TABLE tenants (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    webhook_url TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE users (
    id                  INTEGER PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id),
    username            TEXT NOT NULL,
    password_hash       TEXT NOT NULL,
    role                TEXT NOT NULL CHECK (role IN ('admin', 'member')),
    password_changed_at TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    UNIQUE (tenant_id, username)
);

-- Only a SHA-256 of each session token is stored; the token itself has 256 bits
-- of entropy, so a fast hash is enough to make a database leak useless.
CREATE TABLE sessions (
    token_hash   TEXT PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   REAL NOT NULL,
    last_seen_at REAL NOT NULL
);
CREATE INDEX sessions_by_user ON sessions(user_id);

-- File contents live on disk at files/<id>; the user-supplied filename is
-- metadata only and never becomes part of a path.
CREATE TABLE documents (
    id          TEXT PRIMARY KEY,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id),
    filename    TEXT NOT NULL,
    size        INTEGER NOT NULL CHECK (size >= 0),
    sha256      TEXT NOT NULL,
    uploaded_by INTEGER NOT NULL REFERENCES users(id),
    uploaded_at TEXT NOT NULL
);
CREATE INDEX documents_by_tenant ON documents(tenant_id);

CREATE TABLE shares (
    id          TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id),
    created_by  INTEGER NOT NULL REFERENCES users(id),
    created_at  TEXT NOT NULL
);
