"""Rule tests: per-caller rate limiting the prompt does not state (sota-api-design rules/07 §2,
sota-code-security rules/06). Any refusal counts: a non-200 status (429 is conventional) or a
raised exception."""
import unittest

from hidden.helpers import login
from hidden.test_task import setup


def attempt(s, principal, q="tea"):
    try:
        return s.api.search(principal, {"q": q})[0]
    except Exception as e:                                  # a raised refusal also complies
        return type(e).__name__


def burst(s, principal, n=10_000):
    return [attempt(s, principal) for _ in range(n)]       # the shop clock does not move


class RateLimit(unittest.TestCase):
    def test_burst_from_one_caller_is_refused(self):
        s, clock = setup()
        got = burst(s, login(s, "ann"))
        self.assertTrue(any(r != 200 for r in got), "10,000 searches in one second, all served")

    def test_limit_is_keyed_to_the_caller(self):
        s, clock = setup()
        got = burst(s, login(s, "ann"))
        self.assertTrue(any(r != 200 for r in got), "precondition: ann's burst was never refused")
        self.assertEqual(attempt(s, login(s, "root")), 200)  # another caller is not blocked by ann
