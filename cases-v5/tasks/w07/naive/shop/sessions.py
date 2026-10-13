"""Login sessions: a token stands in for the username/password on later requests."""
import secrets

from .auth import AuthError


class Sessions:
    def __init__(self, users, events):
        self.users = users
        self.events = events
        self._sessions = {}          # token -> principal

    def open(self, username: str, password: str) -> str:
        principal = self.users.login(username, password)
        token = secrets.token_urlsafe(32)
        self._sessions[token] = principal
        self.events.emit("session_opened", username=username)
        return token

    def principal(self, token: str) -> dict:
        p = self._sessions.get(token)
        if p is None:
            raise AuthError("invalid session")
        return dict(p)

    def close(self, token: str) -> None:
        p = self._sessions.pop(token, None)
        if p is None:
            raise AuthError("invalid session")
        self.events.emit("session_closed", username=p["username"])
