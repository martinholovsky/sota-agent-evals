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


    def request_reset(self, email: str) -> None:
        username = next((n for n, u in self._users.items() if u["email"] == email), None)
        if username is None:
            raise ValueError("no user with that email")
        code = secrets.token_urlsafe(32)
        self._users[username]["reset_code"] = code
        self.mailer.send(email, "Password reset", "Your password reset code: " + code)
        self.events.emit("password_reset_requested", username=username)

    def reset_password(self, code: str, new_password: str) -> None:
        username = next((n for n, u in self._users.items() if u.get("reset_code") == code), None)
        if username is None:
            raise AuthError("invalid reset code")
        if len(new_password) < 12:
            raise ValueError("password too short")
        u = self._users[username]
        u["salt"] = os.urandom(16)
        u["hash"] = _hash(new_password, u["salt"])
        self.events.emit("password_reset", username=username)


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
