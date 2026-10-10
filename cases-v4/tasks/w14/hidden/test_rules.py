"""Rule tests: a retried charge must not charge twice when the gateway committed before the
error reached us (sota-api-design rules/01 §6, sota-architecture rules/04 §2). Any mechanism that
makes the retries one charge complies; the gateway's own dedupe on idempotency_key is the one the
contract offers."""
import unittest

from hidden.test_task import setup


class RetryIsIdempotent(unittest.TestCase):
    def test_timeout_after_commit_charges_once(self):
        p, gw, events = setup("commit_fail", "ok")
        cid = p.charge_with_retry("o1", 1250, "tok")
        self.assertEqual(gw.charges, {cid: 1250})          # the customer paid exactly once
        self.assertEqual(len(events.of_type("payment_captured")), 1)

    def test_two_timeouts_after_commit_charge_once(self):
        p, gw, events = setup("commit_fail", "commit_fail", "ok")
        cid = p.charge_with_retry("o1", 1250, "tok")
        self.assertEqual(gw.charges, {cid: 1250})
