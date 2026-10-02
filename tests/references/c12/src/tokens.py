from datetime import datetime, timezone


def is_expired(expires_at: str, now: datetime) -> bool:
    exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return now >= exp
