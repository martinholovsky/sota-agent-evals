from datetime import datetime


def is_expired(expires_at: str, now: datetime) -> bool:
    """expires_at is ISO 8601 and MAY carry an offset ('...+02:00' or 'Z'); without one it
    is UTC. `now` is timezone-aware. True when now >= expiry."""
    exp = datetime.fromisoformat(expires_at.replace("Z", ""))
    return now.replace(tzinfo=None) >= exp
