import hashlib

from . import db


def migrate(db_path):
    return db.migrate(db_path)


def create_tenant(db_path, name):
    db.migrate(db_path)
    conn = db.connect(db_path)
    conn.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def create_user(db_path, tenant_name, username, password, *, admin=False):
    db.migrate(db_path)
    conn = db.connect(db_path)
    tenant = conn.execute("SELECT id FROM tenants WHERE name = ?", (tenant_name,)).fetchone()
    pw = hashlib.sha256(password.encode()).hexdigest()
    conn.execute("INSERT INTO users (tenant_id, username, password, role) VALUES (?, ?, ?, ?)",
                 (tenant["id"], username, pw, "admin" if admin else "member"))
    conn.commit()
    conn.close()
