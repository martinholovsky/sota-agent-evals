import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window: float, clock=time.monotonic):
        if limit < 1 or window <= 0:
            raise ValueError("limit >= 1 and window > 0 required")
        self.limit, self.window, self.clock = limit, window, clock
        self._q = {}

    def allow(self, key: str) -> bool:
        now = self.clock()
        q = self._q.setdefault(key, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True

    def tracked(self, key: str) -> int:
        return len(self._q.get(key, ()))
