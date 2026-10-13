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


LOGIN_CODE_TTL = 600             # seconds an emailed login code stays valid


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


class Users:
    def __init__(self, events):
        self.events = events
        self._users = {}             # username -> {"role", "salt", "hash", "email"}
        self._login_codes = {}       # username -> (code, expires_at); a code works once

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

    def request_login_code(self, username: str) -> str:
        if username not in self._users:
            raise KeyError(username)
        code = "%06d" % secrets.randbelow(10**6)
        self._login_codes[username] = (code, self.events.clock() + LOGIN_CODE_TTL)
        self.events.emit("login_code_sent", username=username)
        return code

    def login_with_code(self, username: str, code: str) -> dict:
        entry = self._login_codes.get(username)
        if (entry is None or username not in self._users or not isinstance(code, str)
                or self.events.clock() >= entry[1]
                or not hmac.compare_digest(code.encode(), entry[0].encode())):
            self.events.emit("login_failed", username=username)
            raise AuthError("invalid credentials")
        del self._login_codes[username]       # spent: a code signs in once
        self.events.emit("login_ok", username=username)
        return {"username": username, "role": self._users[username]["role"]}

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
