import time


class RateLimiter:
    """Per-key token bucket. Each key starts with `capacity` tokens and regains `rate`
    tokens per second, never above capacity. allow(key) spends one token and returns True,
    or returns False (spending nothing) when fewer than one token remains. `clock` returns
    seconds (monotonic); tests inject it. capacity < 1 or rate <= 0 raises ValueError."""

    def __init__(self, capacity: int, rate: float, clock=time.monotonic):
        raise NotImplementedError

    def allow(self, key: str) -> bool:
        raise NotImplementedError
