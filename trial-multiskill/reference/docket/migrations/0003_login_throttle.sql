-- 0003: per-account failed-login counter used to throttle password guessing.

CREATE TABLE login_throttle (
    tenant_name  TEXT NOT NULL,
    username     TEXT NOT NULL,
    failures     INTEGER NOT NULL,
    window_start REAL NOT NULL,
    locked_until REAL,
    PRIMARY KEY (tenant_name, username)
);
