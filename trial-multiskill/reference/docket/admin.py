"""Administrative operations shared by the CLI and tests."""
import datetime
import json
import logging
import re
import sqlite3

from . import db, security

activity = logging.getLogger("docket.activity")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class AdminError(Exception):
    pass


def _now_iso():
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def migrate(db_path):
    return db.migrate(db_path)


def create_tenant(db_path, name):
    if not isinstance(name, str) or not _NAME.match(name):
        raise AdminError("tenant name must be 1-64 characters: letters, digits, '.', '_', '-'")
    db.migrate(db_path)
    conn = db.connect(db_path)
    try:
        conn.execute("INSERT INTO tenants (name, created_at) VALUES (?, ?)", (name, _now_iso()))
    except sqlite3.IntegrityError:
        raise AdminError(f"tenant {name!r} already exists") from None
    finally:
        conn.close()
    activity.info(json.dumps({"action": "tenant.created", "tenant": name}))


def create_user(db_path, tenant_name, username, password, *, admin=False):
    if not isinstance(username, str) or not _NAME.match(username):
        raise AdminError("username must be 1-64 characters: letters, digits, '.', '_', '-'")
    problem = security.password_problem(password)
    if problem:
        raise AdminError(problem)
    db.migrate(db_path)
    password_hash = security.hash_password(password)
    conn = db.connect(db_path)
    try:
        row = conn.execute("SELECT id FROM tenants WHERE name = ?", (tenant_name,)).fetchone()
        if row is None:
            raise AdminError(f"no such tenant: {tenant_name!r}")
        now = _now_iso()
        try:
            conn.execute(
                "INSERT INTO users (tenant_id, username, password_hash, role, password_changed_at, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (row["id"], username, password_hash, "admin" if admin else "member", now, now))
        except sqlite3.IntegrityError:
            raise AdminError(f"user {username!r} already exists in tenant {tenant_name!r}") from None
    finally:
        conn.close()
    activity.info(json.dumps({"action": "user.created", "tenant": tenant_name, "username": username,
                              "role": "admin" if admin else "member"}))
