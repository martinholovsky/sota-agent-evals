"""Rule tests: replay protection the prompt does not state (sota-api-design rules/06 §2-§3)."""
import unittest

from hidden.test_task import deliver, ev, setup


class Replay(unittest.TestCase):
    def test_stale_timestamp_is_rejected(self):
        s, clock, o = setup()
        status, _ = deliver(s, ev(o["charge_id"]), clock.t - 3600)     # validly signed, 1 h old
        self.assertNotEqual(status, 200)
        self.assertEqual(s.orders.get(o["id"])["status"], "paid")
        self.assertEqual(s.events.of_type("order_disputed"), [])

    def test_future_timestamp_is_rejected(self):
        s, clock, o = setup()
        status, _ = deliver(s, ev(o["charge_id"]), clock.t + 3600)
        self.assertNotEqual(status, 200)
        self.assertEqual(s.events.of_type("order_disputed"), [])

    def test_duplicate_event_id_is_processed_once(self):
        s, clock, o = setup()
        deliver(s, ev(o["charge_id"]), clock.t)
        deliver(s, ev(o["charge_id"]), clock.t + 5)                    # provider retry, re-signed
        self.assertEqual(len(s.events.of_type("order_disputed")), 1)
