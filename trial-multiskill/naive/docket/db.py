import os
import sqlite3

MIGRATIONS = os.path.join(os.path.dirname(__file__), "migrations")


def connect(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def migrate(db_path):
    conn = connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY)")
    done = {r[0] for r in conn.execute("SELECT name FROM migrations")}
    applied = []
    for name in sorted(os.listdir(MIGRATIONS)):
        if name.endswith(".sql") and name not in done:
            with open(os.path.join(MIGRATIONS, name)) as f:
                conn.executescript(f.read())
            conn.execute("INSERT INTO migrations (name) VALUES (?)", (name,))
            conn.commit()
            applied.append(name)
    conn.close()
    return applied
