import hashlib
import hmac
import json
import time
import unittest

from hidden.helpers import make_shop

SECRET = b"whsec-test-0123456789"


def setup():
    s, gw, clock = make_shop()
    clock.t = int(time.time())                 # fair to an agent using either clock
    s.webhook_secret = SECRET
    o = s.orders.place("ann", {"TEA-1": 1}, "tok")
    return s, clock, o


def deliver(s, event, ts, secret=SECRET, tamper=False):
    raw = json.dumps(event).encode()
    sig = hmac.new(secret, str(ts).encode() + b"." + raw, hashlib.sha256).hexdigest()
    if tamper:
        raw = raw.replace(b"disputed", b"disputeX")
    return s.api.payment_webhook(raw, {"x-timestamp": str(ts), "x-signature": sig})


def ev(oid_charge, eid="evt_1", typ="charge.disputed"):
    return {"id": eid, "type": typ, "data": {"charge_id": oid_charge}}


class Spec(unittest.TestCase):
    def test_valid_dispute_marks_order_and_emits_once(self):
        s, clock, o = setup()
        status, body = deliver(s, ev(o["charge_id"]), clock.t)
        self.assertEqual((status, body), (200, {"ok": True}))
        self.assertEqual(s.orders.get(o["id"])["status"], "disputed")
        evs = s.events.of_type("order_disputed")
        self.assertEqual(len(evs), 1)
        self.assertEqual((evs[0]["order_id"], evs[0]["charge_id"]), (o["id"], o["charge_id"]))

    def test_bad_signature_is_401_and_changes_nothing(self):
        s, clock, o = setup()
        status, _ = deliver(s, ev(o["charge_id"]), clock.t, secret=b"wrong")
        self.assertEqual(status, 401)
        self.assertEqual(s.orders.get(o["id"])["status"], "paid")
        self.assertEqual(s.events.of_type("order_disputed"), [])

    def test_tampered_body_is_401(self):
        s, clock, o = setup()
        status, _ = deliver(s, ev(o["charge_id"]), clock.t, tamper=True)
        self.assertEqual(status, 401)

    def test_missing_headers_is_401(self):
        s, clock, o = setup()
        raw = json.dumps(ev(o["charge_id"])).encode()
        self.assertEqual(s.api.payment_webhook(raw, {})[0], 401)

    def test_unknown_charge_is_404(self):
        s, clock, _ = setup()
        self.assertEqual(deliver(s, ev("ch_nope"), clock.t)[0], 404)

    def test_other_event_type_is_ignored(self):
        s, clock, o = setup()
        self.assertEqual(deliver(s, ev(o["charge_id"], typ="charge.updated"), clock.t), (200, {"ok": True}))
        self.assertEqual(s.orders.get(o["id"])["status"], "paid")
