import time


class RateLimiter:
    def __init__(self, capacity: int, rate: float, clock=time.monotonic):
        if capacity < 1 or rate <= 0:
            raise ValueError("capacity >= 1 and rate > 0 required")
        self.capacity, self.rate, self.clock = capacity, rate, clock
        self._b = {}

    def allow(self, key: str) -> bool:
        now = self.clock()
        tokens, last = self._b.get(key, (float(self.capacity), now))
        tokens = min(self.capacity, tokens + (now - last) * self.rate)
        if tokens < 1:
            self._b[key] = (tokens, now)
            return False
        self._b[key] = (tokens - 1, now)
        return True
