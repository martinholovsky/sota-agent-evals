"""Users and permissions. Roles grant permissions; handlers check permissions, never roles.

ROLE_PERMISSIONS is the single source of truth.
"""
import base64
import hashlib
import hmac
import json
import os

ROLE_PERMISSIONS = {
    "customer": {"order:place", "order:view_own"},
    "admin": {"order:place", "order:view_own", "order:view_any", "order:cancel",
              "catalog:edit", "report:view"},
}


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


SESSION_TTL = 3600
RESET_TTL = 900


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (ValueError, TypeError):
        raise AuthError("invalid token") from None


class Users:
    def __init__(self, events):
        self.events = events
        self._users = {}             # username -> {"role", "salt", "hash", "email"}
        self._token_key = os.urandom(32)

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

    def _make_token(self, username: str, ttl: int, use: str) -> str:
        if username not in self._users:
            raise KeyError(username)
        claims = {"sub": username, "exp": self.events.clock() + ttl, "use": use}
        body = _b64(json.dumps(claims, separators=(",", ":")).encode())
        sig = _b64(hmac.new(self._token_key, body.encode(), hashlib.sha256).digest())
        return body + "." + sig

    def _read_token(self, token, use: str) -> str:
        """The username in a valid token; AuthError otherwise."""
        if not isinstance(token, str) or token.count(".") != 1:
            raise AuthError("invalid token")
        body, sig = token.split(".")
        want = _b64(hmac.new(self._token_key, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig.encode(), want.encode()):
            raise AuthError("invalid token")
        try:
            claims = json.loads(_unb64(body))
        except ValueError:
            raise AuthError("invalid token") from None
        if not isinstance(claims, dict) or not isinstance(claims.get("exp"), int):
            raise AuthError("invalid token")
        if claims.get("use") != use:          # a reset link is not a session, and vice versa
            raise AuthError("invalid token")
        if self.events.clock() >= claims["exp"] or claims.get("sub") not in self._users:
            raise AuthError("invalid token")
        return claims["sub"]

    def session_token(self, username: str) -> str:
        return self._make_token(username, SESSION_TTL, "session")

    def principal_from_session(self, token: str) -> dict:
        username = self._read_token(token, "session")
        return {"username": username, "role": self._users[username]["role"]}

    def reset_token(self, username: str) -> str:
        return self._make_token(username, RESET_TTL, "reset")

    def reset_password(self, token: str, new_password: str) -> None:
        username = self._read_token(token, "reset")
        if not isinstance(new_password, str) or len(new_password) < 12:
            raise ValueError("password too short")
        salt = os.urandom(16)
        u = self._users[username]
        u["salt"], u["hash"] = salt, _hash(new_password, salt)
        self.events.emit("password_reset", username=username)

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
