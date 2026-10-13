"""Users and permissions. Roles grant permissions; handlers check permissions, never roles.

ROLE_PERMISSIONS is the single source of truth.
"""
import hashlib
import hmac
import os
import secrets

ROLE_PERMISSIONS = {
    "customer": {"order:place", "order:view_own"},
    "admin": {"order:place", "order:view_own", "order:view_any", "order:cancel",
              "catalog:edit", "report:view"},
}

LOGIN_CODE_TTL = 600             # seconds


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


class Users:
    def __init__(self, events, outbox=None):
        self.events = events
        self.outbox = outbox
        self._users = {}             # username -> {"role", "salt", "hash", "email"}

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

    def request_login_code(self, username: str) -> None:
        u = self._users.get(username)
        if u is None:
            return
        code = "%06d" % secrets.randbelow(10 ** 6)
        u["login_code"] = {"code": code, "issued": self.events.clock()}
        self.events.emit("login_code_sent", username=username)
        self.outbox.send(u["email"], "Your login code", "Your login code: %s" % code)

    def login_with_code(self, username: str, code) -> dict:
        u = self._users.get(username)
        pending = u.get("login_code") if u is not None else None
        ok = (pending is not None and isinstance(code, str)
              and self.events.clock() - pending["issued"] < LOGIN_CODE_TTL
              and hmac.compare_digest(code.encode(), pending["code"].encode()))
        if not ok:
            self.events.emit("login_failed", username=username)
            raise AuthError("invalid credentials")
        del u["login_code"]
        self.events.emit("login_ok", username=username)
        return {"username": username, "role": u["role"]}

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
