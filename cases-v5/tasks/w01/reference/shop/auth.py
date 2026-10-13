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


TOKEN_TTL = 3600                 # seconds a login token stays valid


class AuthError(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


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

    def _token_mac(self, body: str) -> str:
        return _b64(hmac.new(self._token_key, body.encode(), hashlib.sha256).digest())

    def issue_token(self, principal: dict) -> str:
        """A self-contained token: base64url(JSON claims) + "." + base64url(HMAC-SHA256)."""
        claims = {"sub": principal["username"], "role": principal["role"],
                  "exp": self.events.clock() + TOKEN_TTL}
        body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        self.events.emit("token_issued", username=principal["username"])
        return body + "." + self._token_mac(body)

    def principal_from_token(self, token: str) -> dict:
        if not isinstance(token, str) or token.count(".") != 1:
            raise AuthError("invalid token")
        body, mac = token.split(".")
        # Check the MAC before looking at anything the token claims.
        if not hmac.compare_digest(mac.encode(), self._token_mac(body).encode()):
            raise AuthError("invalid token")
        try:
            claims = json.loads(_unb64(body))
        except ValueError:
            raise AuthError("invalid token") from None
        if (not isinstance(claims, dict) or not isinstance(claims.get("sub"), str)
                or not isinstance(claims.get("role"), str)
                or not isinstance(claims.get("exp"), int)):
            raise AuthError("invalid token")
        if self.events.clock() >= claims["exp"]:
            raise AuthError("token expired")
        return {"username": claims["sub"], "role": claims["role"]}

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
