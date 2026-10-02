import time


class SlidingWindowLimiter:
    """allow(key) returns True if fewer than `limit` calls for that key were ALLOWED in the
    last `window` seconds (a call at time t counts while now - t < window), and records the
    call; otherwise returns False and records nothing. Keys are independent. Memory for a
    key must not grow without bound: timestamps older than the window are discarded.
    limit < 1 or window <= 0 raises ValueError. `clock` is injectable (seconds)."""

    def __init__(self, limit: int, window: float, clock=time.monotonic):
        raise NotImplementedError

    def allow(self, key: str) -> bool:
        raise NotImplementedError

    def tracked(self, key: str) -> int:
        """How many timestamps are currently stored for key (for tests)."""
        raise NotImplementedError
