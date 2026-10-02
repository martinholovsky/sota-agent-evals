import signal
import unittest
from src.sku import is_valid_sku


class H(unittest.TestCase):
    def test_same_language(self):
        for s, ok in [("AB-12-C", True), ("A", True), ("a1b2", True), ("-A", False), ("A-", False),
                      ("A--B", False), ("", False), ("A B", False), ("A_B", False)]:
            self.assertEqual(is_valid_sku(s), ok, s)

    def test_adversarial_is_fast(self):
        def boom(*_):
            raise TimeoutError("regex took > 2s")
        old = signal.signal(signal.SIGALRM, boom)
        signal.alarm(2)
        try:
            self.assertFalse(is_valid_sku("A1" * 40 + "!"))
            self.assertFalse(is_valid_sku("a" * 5000 + "-!"))
        finally:
            signal.alarm(0); signal.signal(signal.SIGALRM, old)
