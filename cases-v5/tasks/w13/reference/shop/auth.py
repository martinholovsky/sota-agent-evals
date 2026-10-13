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


# Recovery codes use an alphabet without look-alike characters (no 0/O, 1/I/L).
RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_recovery_code() -> str:
    """One printable recovery code, e.g. 'K7QM-2XPA-RT9C-HW4N' (four groups of four)."""
    return "-".join("".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(4))
                    for _ in range(4))


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

    def generate_recovery_codes(self, username: str) -> list:
        u = self._users[username]
        codes = []
        while len(codes) < 10:
            c = new_recovery_code()
            if c not in codes:
                codes.append(c)
        # Only a salted, slow hash of each code is kept; the codes themselves are returned once.
        stored = []
        for c in codes:
            salt = os.urandom(16)
            stored.append({"salt": salt, "hash": _hash(c, salt), "used": False})
        u["recovery_codes"] = stored
        self.events.emit("recovery_codes_generated", username=username, count=len(codes))
        return codes

    def use_recovery_code(self, username: str, code: str) -> bool:
        u = self._users.get(username)
        if u is None or not isinstance(code, str):
            return False
        for entry in u.get("recovery_codes", []):
            if not entry["used"] and hmac.compare_digest(_hash(code, entry["salt"]), entry["hash"]):
                entry["used"] = True
                self.events.emit("recovery_code_used", username=username,
                                 remaining=self.recovery_codes_left(username))
                return True
        return False

    def recovery_codes_left(self, username: str) -> int:
        u = self._users.get(username)
        if u is None:
            return 0
        return sum(1 for e in u.get("recovery_codes", []) if not e["used"])

    def email_of(self, username: str) -> str:
        return self._users[username]["email"]


def can(principal: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(principal["role"], set())


def require(principal: dict, permission: str) -> None:
    if not can(principal, permission):
        raise AuthError("forbidden: %s" % permission)
