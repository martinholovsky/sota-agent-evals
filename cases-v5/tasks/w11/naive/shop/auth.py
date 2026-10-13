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
              "catalog:edit", "report:view", "user:reset_password"},
}


RESET_TTL = 3600                # seconds a reset code stays valid


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


class Users:
    def __init__(self, events, outbox=None):
        self.events = events
        self.outbox = outbox         # shop.outbox: messages to users (see shop/outbox.py)
        self._resets = {}            # username -> pending reset
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
        if (u is None or u["hash"] is None      # None: password reset pending
                or not hmac.compare_digest(_hash(password, u["salt"]), u["hash"])):
            self.events.emit("login_failed", username=username)
            raise AuthError("invalid credentials")
        self.events.emit("login_ok", username=username)
        return {"username": username, "role": u["role"]}

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]

    def start_reset(self, username: str) -> dict:
        u = self._users[username]                       # KeyError for unknown user
        r = {"username": username, "code": secrets.token_urlsafe(16),
             "expires_at": self.events.clock() + RESET_TTL}
        self._resets[username] = r
        u["hash"] = None                                # old password stops working
        self.outbox.send(u["email"], "password_reset", code=r["code"])
        self.events.emit("password_reset_started", username=username)
        return dict(r)

    def complete_reset(self, username: str, code: str, new_password: str) -> None:
        r = self._resets.get(username)
        if (r is None or self.events.clock() > r["expires_at"]
                or not hmac.compare_digest(code.encode(), r["code"].encode())):
            raise AuthError("invalid or expired reset code")
        self._set_password(username, new_password)      # ValueError keeps the code usable
        del self._resets[username]
        self.events.emit("password_reset_completed", username=username)

    def _set_password(self, username: str, password: str) -> None:
        if len(password) < 12:
            raise ValueError("password too short")
        u = self._users[username]
        u["salt"] = os.urandom(16)
        u["hash"] = _hash(password, u["salt"])


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
