import time


class Counter:
    def __init__(self):
        self.value = 0

    def incr(self, n: int = 1) -> int:
        v = self.value
        time.sleep(0)          # stands in for real work between the read and the write
        self.value = v + n
        return self.value
