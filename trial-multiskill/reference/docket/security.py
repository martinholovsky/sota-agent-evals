"""Password hashing and session tokens."""
import base64
import functools
import hashlib
import hmac
import secrets

# PBKDF2-HMAC-SHA256 at the OWASP Password Storage Cheat Sheet work factor.
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 1024  # bounds the work an attacker can make us do per request


def _b64(b):
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def password_problem(password):
    """None if acceptable, else a human-readable reason."""
    if not isinstance(password, str):
        return "password must be a string"
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"password must be at least {MIN_PASSWORD_LENGTH} characters"
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"password must be at most {MAX_PASSWORD_LENGTH} characters"
    return None


def hash_password(password, *, iterations=PBKDF2_ITERATIONS):
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(dk)}"


def verify_password(password, stored):
    try:
        algo, iterations, salt, expected = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _unb64(salt), int(iterations))
        return hmac.compare_digest(dk, _unb64(expected))
    except (ValueError, TypeError, AttributeError):
        return False


@functools.lru_cache(maxsize=1)
def dummy_hash():
    """Verified against when the account does not exist, so a miss costs the same
    time as a wrong password (no user enumeration by timing)."""
    return hash_password(secrets.token_urlsafe(16))


def new_session_token():
    return secrets.token_urlsafe(32)  # 256 bits from the OS CSPRNG


def token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
