-- 0002: outbound webhook queue (transactional outbox written with the upload).

CREATE TABLE webhook_deliveries (
    id              INTEGER PRIMARY KEY,
    event_id        TEXT NOT NULL UNIQUE,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id),
    url             TEXT NOT NULL,
    body            BLOB NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('pending', 'sending', 'delivered', 'failed')),
    attempts        INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL,
    lease_until     REAL,
    last_status     INTEGER,
    last_error      TEXT,
    created_at      REAL NOT NULL
);
CREATE INDEX webhook_deliveries_due ON webhook_deliveries(status, next_attempt_at);
