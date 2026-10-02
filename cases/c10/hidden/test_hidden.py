import threading
import unittest
from src.counter import Counter


class H(unittest.TestCase):
    def test_concurrent(self):
        for _ in range(3):
            c = Counter()
            ts = [threading.Thread(target=lambda: [c.incr() for _ in range(2000)]) for _ in range(8)]
            [t.start() for t in ts]; [t.join() for t in ts]
            self.assertEqual(c.value, 16000)

    def test_returns_new_value_atomically(self):
        c = Counter(); seen = []
        lock = threading.Lock()
        def work():
            for _ in range(500):
                v = c.incr()
                with lock:
                    seen.append(v)
        ts = [threading.Thread(target=work) for _ in range(4)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(sorted(seen), list(range(1, 2001)))
