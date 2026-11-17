"""SQLite connection and forward-only numbered migrations."""
import datetime
import os
import re
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).with_name("migrations")
_MIGRATION_NAME = re.compile(r"^(\d{4})_([A-Za-z0-9_\-]+)\.sql$")


class MigrationError(Exception):
    pass


def connect(db_path):
    """One connection per thread/request. Autocommit mode: transactions are
    opened explicitly with BEGIN IMMEDIATE where atomicity matters."""
    conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def discover_migrations(directory=MIGRATIONS_DIR):
    found = []
    for path in sorted(Path(directory).iterdir()):
        if path.suffix != ".sql":
            continue
        m = _MIGRATION_NAME.match(path.name)
        if not m:
            raise MigrationError(f"migration file name not NNNN_description.sql: {path.name}")
        found.append((int(m.group(1)), path.name, path))
    versions = [v for v, _, _ in found]
    if len(versions) != len(set(versions)):
        raise MigrationError("two migration files share a version number")
    return found


def _statements(sql):
    buf = ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            stmt = buf.strip()
            if stmt.strip(";").strip():
                yield stmt
            buf = ""
    rest = "\n".join(l for l in buf.splitlines() if not l.strip().startswith("--")).strip()
    if rest:
        raise MigrationError("migration ends with an incomplete SQL statement")


def migrate(db_path, directory=MIGRATIONS_DIR):
    """Apply pending migrations in version order, all in one transaction taken
    under the write lock, so concurrent starters cannot apply one twice.
    Returns the names applied. Refuses a pending migration numbered below one
    already applied (forward-only history)."""
    parent = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(parent, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
            applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
            newest = max(applied, default=0)
            done = []
            for version, name, path in discover_migrations(directory):
                if version in applied:
                    continue
                if version < newest:
                    raise MigrationError(
                        f"{name} is older than applied migration {newest:04d}; migrations are forward-only")
                for stmt in _statements(path.read_text(encoding="utf-8")):
                    conn.execute(stmt)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                    (version, name, datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")))
                done.append(name)
            conn.execute("COMMIT")
            return done
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
