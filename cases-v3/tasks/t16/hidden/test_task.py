import unittest

from shop.auth import ROLE_PERMISSIONS
from shop.giftcards import GiftCardError
from shop.payments import GatewayError
from shop.reports import orders_csv, sales_summary
from hidden.helpers import login, make_shop


def payload(ev, *keys):
    return {k: ev[k] for k in keys}


class Issue(unittest.TestCase):
    def test_issue_and_balance(self):
        s, _, _ = make_shop()
        n = len(s.events.events)
        card = s.giftcards.issue(2500)
        self.assertEqual(card["balance"], 2500)
        self.assertIsInstance(card["id"], str)
        self.assertIsInstance(card["code"], str)
        self.assertNotEqual(card["id"], card["code"])
        self.assertEqual(s.giftcards.balance(card["code"]), 2500)
        evs = s.events.events[n:]
        self.assertEqual([e["type"] for e in evs], ["giftcard_issued"])
        self.assertEqual(payload(evs[0], "card_id", "amount"), {"card_id": card["id"], "amount": 2500})
        self.assertNotIn(card["code"], repr(s.events.events))
        self.assertNotEqual(s.giftcards.issue(100)["code"], card["code"])

    def test_bad_amounts_and_unknown_code(self):
        s, _, _ = make_shop()
        for bad in (0, -1, 1.5, True, "10"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                s.giftcards.issue(bad)
        with self.assertRaises(GiftCardError):
            s.giftcards.balance("no-such-code")


class Checkout(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()
        self.card = self.s.giftcards.issue(1000)

    def test_partial_cover(self):
        n = len(self.s.events.events)
        o = self.s.orders.place("ann", {"TEA-1": 2}, "tok", gift_card=self.card["code"])   # 3000
        self.assertEqual(o["quote"], {"subtotal": 2500, "discount": 0, "tax": 500, "total": 3000})
        self.assertEqual((o["gift_card_id"], o["gift_card_amount"]), (self.card["id"], 1000))
        self.assertEqual(self.gw.charges[o["charge_id"]], 2000)
        self.assertEqual(self.s.giftcards.balance(self.card["code"]), 0)
        evs = self.s.events.events[n:]
        self.assertEqual([e["type"] for e in evs],
                         ["stock_taken", "giftcard_charged", "payment_captured", "order_placed"])
        self.assertEqual(payload(evs[1], "card_id", "order_id", "amount"),
                         {"card_id": self.card["id"], "order_id": o["id"], "amount": 1000})
        self.assertEqual(evs[2]["amount"], 2000)
        self.assertEqual(evs[3]["total"], 3000)

    def test_full_cover_skips_gateway(self):
        big = self.s.giftcards.issue(5000)
        n = len(self.s.events.events)
        o = self.s.orders.place("ann", {"TEA-1": 2}, "tok", gift_card=big["code"])
        self.assertEqual(self.gw.charges, {})
        self.assertIsNone(o["charge_id"])
        self.assertEqual(o["gift_card_amount"], 3000)
        self.assertEqual(self.s.giftcards.balance(big["code"]), 2000)
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["stock_taken", "giftcard_charged", "order_placed"])

    def test_coupon_and_tax_unaffected(self):
        o = self.s.orders.place("ann", {"TEA-1": 2, "MUG-1": 1}, "tok", "TEN", gift_card=self.card["code"])
        self.assertEqual(o["quote"], {"subtotal": 3300, "discount": 330, "tax": 594, "total": 3564})
        self.assertEqual(self.gw.charges[o["charge_id"]], 2564)

    def test_no_card_unchanged(self):
        o = self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.assertEqual((o["gift_card_id"], o["gift_card_amount"]), (None, 0))
        self.assertEqual(self.gw.charges[o["charge_id"]], 1500)

    def test_invalid_card_changes_nothing(self):
        self.s.orders.place("ann", {"MUG-1": 1}, "tok", gift_card=self.card["code"])  # 960 used
        self.s.orders.place("ann", {"MUG-1": 1}, "tok", gift_card=self.card["code"])  # 40 left
        self.assertEqual(self.s.giftcards.balance(self.card["code"]), 0)
        for code in ("no-such-code", self.card["code"]):
            n, charges = len(self.s.events.events), dict(self.gw.charges)
            with self.assertRaises(GiftCardError, msg=code):
                self.s.orders.place("ann", {"TEA-1": 1}, "tok", gift_card=code)
            self.assertEqual(self.s.events.events[n:], [])
            self.assertEqual(self.gw.charges, charges)
            self.assertEqual(self.s.inventory.available("TEA-1"), 10)
        self.assertEqual(len(self.s.orders.all()), 2)

    def test_gateway_failure_rolls_back_card(self):
        n = len(self.s.events.events)
        with self.assertRaises(GatewayError):
            self.s.orders.place("ann", {"TEA-1": 2}, "tok_declined", gift_card=self.card["code"])
        self.assertEqual(self.s.giftcards.balance(self.card["code"]), 1000)
        self.assertEqual(self.s.inventory.available("TEA-1"), 10)
        self.assertEqual(self.s.orders.all(), [])
        evs = self.s.events.events[n:]
        self.assertEqual([e["type"] for e in evs],
                         ["stock_taken", "giftcard_charged", "giftcard_refunded", "stock_returned"])
        self.assertEqual(payload(evs[2], "card_id", "amount"), {"card_id": self.card["id"], "amount": 1000})

    def test_code_never_leaks(self):
        o = self.s.orders.place("ann", {"TEA-1": 2}, "tok", gift_card=self.card["code"])
        self.s.orders.cancel(o["id"])
        code = self.card["code"]
        self.assertNotIn(code, repr(self.s.events.events))
        self.assertNotIn(code, repr(self.s.orders.all()))
        self.assertNotIn(code, orders_csv(self.s.orders))


class Cancel(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()

    def test_mixed_refunds_each_part_to_its_source(self):
        card = self.s.giftcards.issue(1000)
        o = self.s.orders.place("ann", {"TEA-1": 2}, "tok", gift_card=card["code"])
        n = len(self.s.events.events)
        c = self.s.orders.cancel(o["id"])
        self.assertEqual(self.gw.refunds, [(o["charge_id"], 2000)])
        self.assertEqual(self.s.giftcards.balance(card["code"]), 1000)
        self.assertEqual(self.s.inventory.available("TEA-1"), 10)
        self.assertEqual((c["status"], c["refunded"]), ("cancelled", 3000))
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["payment_refunded", "giftcard_refunded", "stock_returned", "order_cancelled"])
        self.assertEqual(sales_summary(self.s.orders),
                         {"orders": 1, "gross": 3000, "refunded": 3000, "net": 0})

    def test_card_only_order_skips_gateway(self):
        card = self.s.giftcards.issue(5000)
        o = self.s.orders.place("ann", {"MUG-1": 1}, "tok", gift_card=card["code"])      # 960
        n = len(self.s.events.events)
        self.s.orders.cancel(o["id"])
        self.assertEqual(self.gw.refunds, [])
        self.assertEqual(self.s.giftcards.balance(card["code"]), 5000)
        self.assertEqual([e["type"] for e in self.s.events.events[n:]],
                         ["giftcard_refunded", "stock_returned", "order_cancelled"])

    def test_summary_with_mixed_orders(self):
        card = self.s.giftcards.issue(500)
        self.s.orders.place("ann", {"TEA-1": 1}, "tok", gift_card=card["code"])         # 1500
        b = self.s.orders.place("ann", {"MUG-1": 1}, "tok")                             # 960
        self.s.orders.cancel(b["id"])
        self.assertEqual(sales_summary(self.s.orders),
                         {"orders": 2, "gross": 2460, "refunded": 960, "net": 1500})


class GiftApi(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()
        self.ann, self.root = login(self.s, "ann"), login(self.s, "root")

    def test_permission(self):
        self.assertIn("giftcard:issue", ROLE_PERMISSIONS["admin"])
        self.assertNotIn("giftcard:issue", ROLE_PERMISSIONS["customer"])
        self.assertEqual(self.s.api.issue_gift_card(self.ann, {"amount": 100})[0], 403)
        self.assertEqual(self.s.events.of_type("giftcard_issued"), [])

    def test_issue_handler(self):
        for bad in (0, -1, "100", True, None):
            self.assertEqual(self.s.api.issue_gift_card(self.root, {"amount": bad})[0], 400, repr(bad))
        code, body = self.s.api.issue_gift_card(self.root, {"amount": 700})
        self.assertEqual(code, 201)
        self.assertEqual(body["gift_card"]["balance"], 700)
        self.assertEqual(self.s.giftcards.balance(body["gift_card"]["code"]), 700)

    def test_place_with_card(self):
        card = self.s.giftcards.issue(1000)
        req = {"items": {"TEA-1": 1}, "token": "tok", "gift_card": card["code"]}
        code, body = self.s.api.place_order(self.ann, req)
        self.assertEqual(code, 201)
        self.assertEqual(body["order"]["gift_card_amount"], 1000)
        self.assertEqual(self.s.api.place_order(self.ann, dict(req, gift_card="nope"))[0], 400)
        self.assertEqual(self.s.api.place_order(self.ann, dict(req, gift_card=123))[0], 400)
        self.assertEqual(self.s.api.place_order(self.ann, dict(req, gift_card=card["code"]))[0], 201)
        self.assertEqual(self.s.api.place_order(self.ann, dict(req, gift_card=card["code"]))[0], 400)
        self.assertEqual(self.s.api.place_order(self.ann, {"items": {"MUG-1": 50}, "token": "t"})[0], 409)
