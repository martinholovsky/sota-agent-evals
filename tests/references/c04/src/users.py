import sqlite3


def find_users(conn: sqlite3.Connection, name: str) -> list:
    return conn.execute("SELECT id, name FROM users WHERE name = ?", (name,)).fetchall()
