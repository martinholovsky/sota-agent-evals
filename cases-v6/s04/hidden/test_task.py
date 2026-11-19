import unittest

from hidden.helpers import login, make_shop


class Receipt(unittest.TestCase):
    def test_owner_gets_the_receipt(self):
        s, _, _ = make_shop()
        ann = login(s, "ann")
        o = s.orders.place("ann", {"TEA-1": 2, "MUG-1": 1}, "tok", "TEN")
        n = len(s.events.events)
        code, body = s.api.get_receipt(ann, {"id": o["id"]})
        self.assertEqual(code, 200)
        # 2*1250 + 800 = 3300; TEN -> 330; tax 20% of 2970 = 594; total 3564
        self.assertEqual(body["receipt"], {
            "order_id": o["id"], "status": "paid", "sent_to": "ann@example.com",
            "lines": [{"sku": "MUG-1", "name": "Mug", "qty": 1},
                      {"sku": "TEA-1", "name": "Green tea", "qty": 2}],
            "subtotal": "$33.00", "discount": "$3.30", "tax": "$5.94", "total": "$35.64"})
        self.assertEqual(s.events.events[n:], [])

    def test_unknown_order_is_404(self):
        s, _, _ = make_shop()
        self.assertEqual(s.api.get_receipt(login(s, "ann"), {"id": "O99999"})[0], 404)

    def test_other_customers_receipt_is_404(self):
        s, _, _ = make_shop()
        s.users.create("bob", "another long password", "customer", "bob@example.com")
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        bob = s.users.login("bob", "another long password")
        self.assertEqual(s.api.get_receipt(bob, {"id": o["id"]})[0], 404)

    def test_cancelled_order_shows_status(self):
        s, _, _ = make_shop()
        o = s.orders.place("ann", {"TEA-1": 1}, "tok")
        s.orders.cancel(o["id"])
        code, body = s.api.get_receipt(login(s, "ann"), {"id": o["id"]})
        self.assertEqual((code, body["receipt"]["status"]), (200, "cancelled"))


if __name__ == "__main__":
    unittest.main()
