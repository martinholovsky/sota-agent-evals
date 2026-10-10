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


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


class Users:
    def __init__(self, events):
        self.events = events
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

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]


    # Session lifetime (sota-code-security rules/17 §2), from server-side time only.
    SESSION_IDLE_S = 30 * 60
    SESSION_ABSOLUTE_S = 8 * 3600

    def start_session(self, username: str, password: str) -> str:
        self.login(username, password)
        token = secrets.token_urlsafe(32)                 # CSPRNG, 256 bits, opaque
        now = self.events.clock()
        self.__dict__.setdefault("_sessions", {})[token] = {
            "username": username, "created": now, "seen": now}
        self.events.emit("session_started", username=username)
        return token

    def session_user(self, token: str):
        sessions = self.__dict__.setdefault("_sessions", {})
        s = sessions.get(token)
        if s is None:
            return None
        now = self.events.clock()
        if now - s["seen"] > self.SESSION_IDLE_S or now - s["created"] > self.SESSION_ABSOLUTE_S:
            del sessions[token]
            return None
        s["seen"] = now
        return s["username"]

    def change_password(self, username: str, old_password: str, new_password: str) -> None:
        self.login(username, old_password)
        if len(new_password) < 12:
            raise ValueError("password too short")
        u = self._users[username]
        u["salt"] = os.urandom(16)
        u["hash"] = _hash(new_password, u["salt"])
        sessions = self.__dict__.setdefault("_sessions", {})
        for t in [t for t, v in sessions.items() if v["username"] == username]:
            del sessions[t]                                # revoke every session of the user
        self.events.emit("password_changed", username=username)


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
