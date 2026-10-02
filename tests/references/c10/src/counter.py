import threading
import time


class Counter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def incr(self, n: int = 1) -> int:
        with self._lock:
            v = self.value
            time.sleep(0)
            self.value = v + n
            return self.value
