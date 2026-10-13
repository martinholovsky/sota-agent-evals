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


IDLE_TIMEOUT = 30 * 60          # seconds since last use
# Hard cap on a session's life however active it is; after it the user logs in again.
# 12 hours covers a working day of shopping or back-office use.
ABSOLUTE_LIFETIME = 12 * 3600


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


class Users:
    def __init__(self, events):
        self.events = events
        self._users = {}             # username -> {"role", "salt", "hash", "email"}
        self._sessions = {}          # token -> {"username", "last_used", "started"}

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

    def start_session(self, username: str, password: str) -> str:
        self.login(username, password)          # raises AuthError, emits login_ok/failed
        token = secrets.token_urlsafe(32)
        now = self.events.clock()
        self._sessions[token] = {"username": username, "last_used": now, "started": now}
        self.events.emit("session_started", username=username)
        return token

    def principal_for(self, token: str) -> dict:
        s = self._sessions.get(token)
        now = self.events.clock()
        if (s is None or now - s["last_used"] > IDLE_TIMEOUT
                or now - s["started"] > ABSOLUTE_LIFETIME):
            raise AuthError("invalid session")
        s["last_used"] = now
        return {"username": s["username"], "role": self._users[s["username"]]["role"]}

    def end_session(self, token: str) -> None:
        s = self._sessions.pop(token, None)
        if s is None:
            raise AuthError("invalid session")
        self.events.emit("session_ended", username=s["username"])


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
