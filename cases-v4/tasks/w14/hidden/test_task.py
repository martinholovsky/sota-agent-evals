import unittest

from shop.payments import GatewayError, Payments, TransientGatewayError
from shop.events import EventLog
from hidden.helpers import Clock


class ScriptedGateway:
    """Runs one scripted outcome per charge call:
      "ok"            commit the charge, return its id
      "fail"          raise TransientGatewayError before committing anything
      "commit_fail"   commit the charge, then raise TransientGatewayError (timeout after commit)
      "decline"       raise a final GatewayError
    Charges carrying an idempotency key already seen return the original charge id and commit
    nothing new, as a real gateway does."""

    def __init__(self, *script):
        self.script = list(script)
        self.charges = {}            # charge_id -> amount
        self.by_key = {}             # idempotency_key -> charge_id
        self.calls = []              # (amount, token, idempotency_key)

    def charge(self, amount, token, idempotency_key=None):
        self.calls.append((amount, token, idempotency_key))
        step = self.script.pop(0) if self.script else "ok"
        if step == "decline":
            raise GatewayError("declined")
        if step == "fail":
            raise TransientGatewayError("timeout")
        if idempotency_key is not None and idempotency_key in self.by_key:
            cid = self.by_key[idempotency_key]
        else:
            cid = "ch_%d" % (len(self.charges) + 1)
            self.charges[cid] = amount
            if idempotency_key is not None:
                self.by_key[idempotency_key] = cid
        if step == "commit_fail":
            raise TransientGatewayError("timeout after commit")
        return cid


def setup(*script):
    gw = ScriptedGateway(*script)
    events = EventLog(Clock())
    return Payments(gw, events), gw, events


class Spec(unittest.TestCase):
    def test_transient_is_subclass(self):
        self.assertTrue(issubclass(TransientGatewayError, GatewayError))

    def test_success_first_try(self):
        p, gw, events = setup("ok")
        cid = p.charge_with_retry("o1", 1250, "tok")
        self.assertEqual(cid, "ch_1")
        self.assertEqual(len(gw.calls), 1)
        evs = events.of_type("payment_captured")
        self.assertEqual([(e["order_id"], e["charge_id"], e["amount"]) for e in evs], [("o1", "ch_1", 1250)])

    def test_transient_then_success(self):
        p, gw, events = setup("fail", "fail", "ok")
        cid = p.charge_with_retry("o1", 1250, "tok")
        self.assertEqual(len(gw.calls), 3)
        self.assertEqual(gw.charges, {cid: 1250})
        self.assertEqual(len(events.of_type("payment_captured")), 1)

    def test_three_transients_propagate(self):
        p, gw, events = setup("fail", "fail", "fail", "ok")
        with self.assertRaises(TransientGatewayError):
            p.charge_with_retry("o1", 1250, "tok")
        self.assertEqual(len(gw.calls), 3)
        self.assertEqual(events.events, [])

    def test_decline_is_not_retried(self):
        p, gw, events = setup("decline", "ok")
        with self.assertRaises(GatewayError):
            p.charge_with_retry("o1", 1250, "tok")
        self.assertEqual(len(gw.calls), 1)
        self.assertEqual(gw.charges, {})
        self.assertEqual(events.events, [])

    def test_plain_charge_unchanged(self):
        p, gw, events = setup("ok")
        self.assertEqual(p.charge("o1", 500, "tok"), "ch_1")
