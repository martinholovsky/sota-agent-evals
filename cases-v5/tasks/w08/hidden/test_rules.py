import unittest

from hidden.helpers import make_shop


class RefundLogRules(unittest.TestCase):
    def test_refund_events_record_who_did_it(self):
        """V16.2.1: the record of a refund must let an investigator tell when it happened, to
        what, and who did it. The time ("at") and the order id are already there; this checks
        the acting admin's username appears in the events the refund emits, under any key."""
        s, _, _ = make_shop()
        s.users.create("carol", "carol's long password", "admin", "carol@example.com")
        o = s.orders.place("ann", {"TEA-1": 2}, "tok")
        carol = s.users.login("carol", "carol's long password")
        n = len(s.events.events)
        code, _ = s.api.refund_order(carol, {"id": o["id"], "amount": 500})
        self.assertEqual(code, 200)
        new = s.events.events[n:]
        self.assertTrue(new)
        self.assertTrue(all("at" in e for e in new))
        self.assertTrue(any(o["id"] in repr(e) for e in new))
        self.assertTrue(any("carol" in repr(list(e.values())) for e in new),
                        "no refund event names the admin who issued it: %r" % new)
