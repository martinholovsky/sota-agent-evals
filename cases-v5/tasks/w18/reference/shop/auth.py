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

RESET_CODE_TTL = 15 * 60         # seconds
RESET_MAX_FAILURES = 5          # wrong codes before a code is voided


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


def _check_password(password: str) -> None:
    if len(password) < 12:
        raise ValueError("password too short")


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
        _check_password(password)
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

    def request_password_reset(self, username: str) -> None:
        u = self._users.get(username)
        if u is None:
            return
        code = "%06d" % secrets.randbelow(10 ** 6)
        u["reset"] = {"code": code, "issued": self.events.clock(), "failures": 0}
        self.events.emit("password_reset_requested", username=username)
        self.outbox.send(u["email"], "Password reset", "Your password reset code: %s" % code)

    def reset_password(self, username: str, code, new_password: str) -> None:
        u = self._users.get(username)
        pending = u.get("reset") if u is not None else None
        ok = (pending is not None and isinstance(code, str)
              and self.events.clock() - pending["issued"] < RESET_CODE_TTL
              and hmac.compare_digest(code.encode(), pending["code"].encode()))
        if not ok:
            if pending is not None:
                pending["failures"] += 1
                if pending["failures"] >= RESET_MAX_FAILURES:
                    del u["reset"]           # too many wrong codes: a new code must be requested
            self.events.emit("password_reset_failed", username=username)
            raise AuthError("invalid or expired reset code")
        _check_password(new_password)
        salt = os.urandom(16)
        u["salt"], u["hash"] = salt, _hash(new_password, salt)
        del u["reset"]
        self.events.emit("password_reset", username=username)

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
