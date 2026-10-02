"""Users and permissions. Roles grant permissions; handlers check permissions, never roles.

ROLE_PERMISSIONS is the single source of truth.
"""
import hashlib
import hmac
import os

ROLE_PERMISSIONS = {
    "customer": {"order:place", "order:view_own"},
    "admin": {"order:place", "order:view_own", "order:view_any", "order:cancel",
              "catalog:edit", "report:view", "user:unlock"},
}

LOCKOUT_THRESHOLD = 5        # counted failures that lock a username
LOCKOUT_WINDOW = 300         # seconds a failure keeps counting
LOCKOUT_DURATION = 900       # seconds a lock lasts


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


class Users:
    def __init__(self, events):
        self.events = events
        self._users = {}             # username -> {"role", "salt", "hash", "email"}
        self._failures = {}          # username -> [clock times of counted failures]
        self._locked = {}            # username -> locked until (clock time)

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

    def _now(self) -> int:
        return self.events.clock()

    def _lock_until(self, username: str):
        """The lock end time if `username` is locked now; clears an expired lock."""
        until = self._locked.get(username)
        if until is not None and self._now() >= until:
            del self._locked[username]           # lock ran out: start over
            self._failures.pop(username, None)
            until = None
        return until

    def login(self, username: str, password: str) -> dict:
        if self._lock_until(username) is not None:      # before the password is checked
            self.events.emit("login_locked", username=username)
            raise AuthError("invalid credentials")
        u = self._users.get(username)
        if u is None or not hmac.compare_digest(_hash(password, u["salt"]), u["hash"]):
            now = self._now()
            recent = [t for t in self._failures.get(username, []) if now - t < LOCKOUT_WINDOW]
            recent.append(now)
            self.events.emit("login_failed", username=username)
            if len(recent) >= LOCKOUT_THRESHOLD:
                self._failures.pop(username, None)
                self._locked[username] = now + LOCKOUT_DURATION
                self.events.emit("account_locked", username=username, until=now + LOCKOUT_DURATION)
            else:
                self._failures[username] = recent
            raise AuthError("invalid credentials")
        self._failures.pop(username, None)
        self.events.emit("login_ok", username=username)
        return {"username": username, "role": u["role"]}

    def unlock(self, username: str) -> None:
        if username not in self._users:
            raise KeyError(username)
        if self._lock_until(username) is None:
            raise ValueError("user is not locked")
        del self._locked[username]
        self._failures.pop(username, None)
        self.events.emit("account_unlocked", username=username)

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
