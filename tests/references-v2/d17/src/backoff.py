from email.utils import parsedate_to_datetime


def next_delay(attempt: int, retry_after, now_epoch: float, base: float = 0.5, cap: float = 30.0) -> float:
    if attempt < 1:
        raise ValueError(attempt)
    if retry_after is not None:
        s = retry_after.strip()
        if s.isdigit():
            return float(min(cap, int(s)))
        try:
            dt = parsedate_to_datetime(s)
        except (TypeError, ValueError, IndexError):
            raise ValueError(retry_after)
        if dt is None:
            raise ValueError(retry_after)
        return float(min(cap, max(0.0, dt.timestamp() - now_epoch)))
    return float(min(cap, base * 2 ** (attempt - 1)))
