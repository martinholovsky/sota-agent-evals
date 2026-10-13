"""Login sessions: a token stands in for the username/password on later requests.

A session that goes unused for IDLE_TIMEOUT seconds ends; the user must log in again.
"""
import secrets

from .auth import AuthError

IDLE_TIMEOUT = 30 * 60       # seconds without a request before the session ends


class Sessions:
    def __init__(self, users, events):
        self.users = users
        self.events = events
        self._sessions = {}          # token -> {"principal", "last_seen"}

    def open(self, username: str, password: str) -> str:
        principal = self.users.login(username, password)
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {"principal": principal, "last_seen": self.events.clock()}
        self.events.emit("session_opened", username=username)
        return token

    def principal(self, token: str) -> dict:
        s = self._sessions.get(token)
        if s is None:
            raise AuthError("invalid session")
        now = self.events.clock()
        if now - s["last_seen"] > IDLE_TIMEOUT:
            del self._sessions[token]
            self.events.emit("session_expired", username=s["principal"]["username"])
            raise AuthError("invalid session")
        s["last_seen"] = now
        return dict(s["principal"])

    def close(self, token: str) -> None:
        s = self._sessions.pop(token, None)
        if s is None:
            raise AuthError("invalid session")
        self.events.emit("session_closed", username=s["principal"]["username"])
