import hashlib
import hmac
import json
import unittest

from hidden.helpers import login, make_shop

SECRET = b"whsec_test_0123456789"


def sign(secret, ts, body):
    return hmac.new(secret, ("%s.%s" % (ts, body)).encode(), hashlib.sha256).hexdigest()


def dispute_body(eid, cid):
    return json.dumps({"id": eid, "type": "charge.disputed", "data": {"charge_id": cid}})


class Webhook(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, self.clock = make_shop()
        self.s.payments.webhook_secret = SECRET
        self.o = self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.cid = self.o["charge_id"]

    def send(self, body, ts=None, sig=None, secret=SECRET):
        ts = str(self.clock.t) if ts is None else ts
        sig = sign(secret, ts, body) if sig is None else sig
        return self.s.api.payment_webhook(
            {"headers": {"Shop-Timestamp": ts, "Shop-Signature": sig}, "body": body})

    def status(self):
        return self.s.orders.get(self.o["id"])["status"]

    def test_valid_dispute(self):
        n = len(self.s.events.events)
        code, body = self.send(dispute_body("evt_1", self.cid))
        self.assertEqual(code, 200)
        self.assertEqual(body["order"]["status"], "disputed")
        self.assertEqual(self.status(), "disputed")
        new = self.s.events.events[n:]
        self.assertEqual([e["type"] for e in new], ["order_disputed"])
        self.assertEqual((new[0]["order_id"], new[0]["event_id"]), (self.o["id"], "evt_1"))

    def test_signature_over_raw_body_not_reserialized(self):
        raw = '{"type":"charge.disputed",   "data": {"charge_id": "%s"},"id":"evt_raw"}' % self.cid
        self.assertEqual(self.send(raw)[0], 200)
        self.assertEqual(self.status(), "disputed")

    def test_bad_signatures_are_401_and_change_nothing(self):
        body = dispute_body("evt_1", self.cid)
        n = len(self.s.events.events)
        ts = str(self.clock.t)
        for sig in ("0" * 64, sign(b"wrong secret", ts, body), sign(SECRET, ts, body)[:-1],
                    sign(SECRET, ts, body) + "0", "zz", "é" * 64):
            self.assertEqual(self.send(body, ts=ts, sig=sig)[0], 401, msg=repr(sig))
        # signature computed for another timestamp
        self.assertEqual(self.send(body, ts=ts, sig=sign(SECRET, str(self.clock.t - 1), body))[0], 401)
        self.assertEqual(self.status(), "paid")
        self.assertEqual(len(self.s.events.events), n)

    def test_timestamp_tolerance_both_directions(self):
        t = self.clock.t
        for i, (ts, want) in enumerate([(t - 301, 401), (t + 301, 401),
                                        (t - 300, 200), (t + 300, 200)]):
            body = json.dumps({"id": "evt_t%d" % i, "type": "charge.refunded", "data": {}})
            self.assertEqual(self.send(body, ts=str(ts))[0], want, msg=ts - t)

    def test_malformed_requests_are_400(self):
        body = dispute_body("evt_1", self.cid)
        ts = str(self.clock.t)
        good = sign(SECRET, ts, body)
        api = self.s.api.payment_webhook
        self.assertEqual(api({"headers": {"Shop-Signature": good}, "body": body})[0], 400)
        self.assertEqual(api({"headers": {"Shop-Timestamp": ts}, "body": body})[0], 400)
        self.assertEqual(api({"body": body})[0], 400)
        self.assertEqual(api({"headers": {"Shop-Timestamp": ts, "Shop-Signature": good}})[0], 400)
        self.assertEqual(self.send(body, ts="12abc", sig=good)[0], 400)
        for bad in ("not json", "[1, 2]", json.dumps({"type": "charge.disputed"}),
                    json.dumps({"id": "evt_x", "type": "charge.disputed", "data": {}})):
            self.assertEqual(self.send(bad)[0], 400, msg=bad)
        self.assertEqual(self.status(), "paid")

    def test_unconfigured_secret_rejects_everything(self):
        self.s.payments.webhook_secret = None
        body = dispute_body("evt_1", self.cid)
        self.assertEqual(self.send(body, secret=b"")[0], 401)
        self.assertEqual(self.status(), "paid")

    def test_replay_is_409(self):
        body = dispute_body("evt_1", self.cid)
        self.assertEqual(self.send(body)[0], 200)
        n = len(self.s.events.events)
        self.clock.t += 10
        self.assertEqual(self.send(body)[0], 409)
        self.assertEqual(len(self.s.events.events), n)
        ign = json.dumps({"id": "evt_2", "type": "charge.succeeded", "data": {}})
        self.assertEqual(self.send(ign)[0], 200)
        self.assertEqual(self.send(ign)[0], 409)
        self.assertEqual(len(self.s.events.events), n)

    def test_rejected_webhook_does_not_consume_its_id(self):
        body = dispute_body("evt_9", self.cid)
        self.assertEqual(self.send(body, sig="0" * 64)[0], 401)
        self.assertEqual(self.send(body, ts=str(self.clock.t - 1000))[0], 401)
        self.assertEqual(self.send(dispute_body("evt_9", "ch_nope"))[0], 404)
        self.assertEqual(self.send(body)[0], 200)
        self.assertEqual(self.status(), "disputed")

    def test_dispute_only_from_paid(self):
        self.s.orders.cancel(self.o["id"])
        n = len(self.s.events.events)
        self.assertEqual(self.send(dispute_body("evt_1", self.cid))[0], 409)
        self.assertEqual(self.status(), "cancelled")
        self.assertEqual(len(self.s.events.events), n)
        o2 = self.s.orders.place("ann", {"MUG-1": 1}, "tok")
        self.assertEqual(self.send(dispute_body("evt_1", o2["charge_id"]))[0], 200)  # id unused
        self.assertEqual(self.send(dispute_body("evt_2", o2["charge_id"]))[0], 409)  # already disputed

    def test_unknown_charge_is_404(self):
        self.assertEqual(self.send(dispute_body("evt_1", "ch_999"))[0], 404)

    def test_disputed_order_cannot_be_cancelled(self):
        self.assertEqual(self.send(dispute_body("evt_1", self.cid))[0], 200)
        self.assertEqual(self.s.api.cancel_order(login(self.s, "root"), {"id": self.o["id"]})[0], 409)
        self.assertEqual(self.gw.refunds, [])

    def test_ignored_types_emit_nothing(self):
        n = len(self.s.events.events)
        body = json.dumps({"id": "evt_5", "type": "charge.refunded", "data": {"charge_id": self.cid}})
        self.assertEqual(self.send(body)[0], 200)
        self.assertEqual(len(self.s.events.events), n)
        self.assertEqual(self.status(), "paid")

    def test_no_secret_or_signature_in_events(self):
        body = dispute_body("evt_1", self.cid)
        sig = sign(SECRET, str(self.clock.t), body)
        self.send(body, sig="f" * 64)
        self.assertEqual(self.send(body, sig=sig)[0], 200)
        dump = repr(self.s.events.events)
        self.assertNotIn(SECRET.decode(), dump)
        self.assertNotIn(sig, dump)
        self.assertNotIn("f" * 64, dump)

    def test_base_flows_unaffected(self):
        o = self.s.orders.place("ann", {"MUG-1": 2}, "tok")
        self.assertEqual(self.s.orders.cancel(o["id"])["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
