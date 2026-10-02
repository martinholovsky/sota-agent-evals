import unittest
from src.retry import retry


class Flaky:
    def __init__(self, fails, exc=OSError):
        self.fails, self.exc, self.calls = fails, exc, 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.fails:
            raise self.exc("boom %d" % self.calls)
        return "ok"


class H(unittest.TestCase):
    def test_backoff_values(self):
        slept = []
        f = Flaky(2)
        self.assertEqual(retry(f, attempts=3, base=0.1, cap=2.0, sleep=slept.append, rand=lambda: 1.0), "ok")
        self.assertEqual(slept, [0.1, 0.2])

    def test_cap(self):
        slept = []
        retry(Flaky(4), attempts=5, base=1.0, cap=2.0, sleep=slept.append, rand=lambda: 1.0)
        self.assertEqual(slept, [1.0, 2.0, 2.0, 2.0])

    def test_exhausted_reraises_last(self):
        with self.assertRaisesRegex(OSError, "boom 3"):
            retry(Flaky(9), attempts=3, sleep=lambda s: None)

    def test_non_retryable_no_sleep(self):
        slept = []
        f = Flaky(1, exc=KeyError)
        with self.assertRaises(KeyError):
            retry(f, retry_on=(OSError,), sleep=slept.append)
        self.assertEqual((f.calls, slept), (1, []))

    def test_bad_attempts(self):
        with self.assertRaises(ValueError):
            retry(lambda: 1, attempts=0)
