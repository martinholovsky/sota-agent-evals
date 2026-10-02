"""Users and permissions. Roles grant permissions; handlers check permissions, never roles.

ROLE_PERMISSIONS is the single source of truth.
"""
import hashlib
import hmac
import os

ROLE_PERMISSIONS = {
    "customer": {"order:place", "order:view_own", "account:delete_own"},
    "admin": {"order:place", "order:view_own", "order:view_any", "order:cancel",
              "catalog:edit", "report:view", "account:delete_own", "user:delete"},
}


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


class Users:
    def __init__(self, events, orders=None):
        self.events = events
        self.orders = orders
        self._users = {}             # username -> {"role", "salt", "hash", "email"}
        self._deleted = 0

    def create(self, username: str, password: str, role: str, email: str) -> None:
        if role not in ROLE_PERMISSIONS:
            raise ValueError("unknown role: %r" % role)
        if username in self._users:
            raise ValueError("duplicate user")
        if len(password) < 12:
            raise ValueError("password too short")
        salt = os.urandom(16)
        self._users[username] = {"role": role, "salt": salt, "hash": _hash(password, salt),
                                 "email": email}
        self.events.emit("user_created", username=username, role=role)

    def login(self, username: str, password: str) -> dict:
        u = self._users.get(username)
        if u is None or not hmac.compare_digest(_hash(password, u["salt"]), u["hash"]):
            self.events.emit("login_failed", username=username)
            raise AuthError("invalid credentials")
        self.events.emit("login_ok", username=username)
        return {"username": username, "role": u["role"]}

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]

    def exists(self, username: str) -> bool:
        return username in self._users

    def delete(self, username: str) -> str:
        """Erase an account: remove it, pseudonymise its orders and past events."""
        if username not in self._users:
            raise KeyError(username)
        self._deleted += 1
        pseudonym = "deleted-%d-%s" % (self._deleted, os.urandom(4).hex())
        if self.orders is not None:
            self.orders.pseudonymise(username, pseudonym)
        for ev in self.events.events:
            for field in ("username", "customer"):
                if ev.get(field) == username:
                    ev[field] = pseudonym
        del self._users[username]
        self.events.emit("user_deleted", pseudonym=pseudonym)
        return pseudonym


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
