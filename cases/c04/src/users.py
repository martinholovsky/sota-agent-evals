import sqlite3


def find_users(conn: sqlite3.Connection, name: str) -> list:
    """Rows (id, name) whose name equals `name` exactly."""
    return conn.execute(f"SELECT id, name FROM users WHERE name = '{name}'").fetchall()
