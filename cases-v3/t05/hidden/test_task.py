import csv
import io
import unittest
from unittest import mock

from shop import auth
from shop.reports import orders_csv, orders_export_csv, sales_summary
from hidden.helpers import login, make_shop

HEADER = ["id", "customer", "email", "status", "items", "subtotal", "discount", "tax",
          "total", "refunded"]
PW = "a long enough password"


def rows(text):
    return list(csv.reader(io.StringIO(text)))


class Export(unittest.TestCase):
    def setUp(self):
        self.s, self.gw, _ = make_shop()

    def test_columns_and_values(self):
        a = self.s.orders.place("ann", {"TEA-1": 2, "MUG-1": 1}, "tok", "TEN")
        b = self.s.orders.place("ann", {"MUG-1": 1}, "tok")
        self.s.orders.cancel(b["id"])
        r = rows(orders_export_csv(self.s.orders, self.s.users))
        self.assertEqual(r[0], HEADER)
        self.assertEqual(r[1], [a["id"], "ann", "ann@example.com", "paid", "MUG-1:1;TEA-1:2",
                                "$33.00", "$3.30", "$5.94", "$35.64", "$0.00"])
        self.assertEqual(r[2], [b["id"], "ann", "ann@example.com", "cancelled", "MUG-1:1",
                                "$8.00", "$0.00", "$1.60", "$9.60", "$9.60"])
        self.assertEqual(len(r), 3)

    def test_sorted_by_id_and_unknown_customer_has_empty_email(self):
        ids = []
        for who in ("ann", "ghost-user", "root"):
            ids.append(self.s.orders.place(who, {"MUG-1": 1}, "tok")["id"])
        r = rows(orders_export_csv(self.s.orders, self.s.users))
        self.assertEqual([x[0] for x in r[1:]], sorted(ids))
        self.assertEqual([x[2] for x in r[1:]], ["ann@example.com", "", "root@example.com"])

    def test_formula_injection_neutralised_in_every_column(self):
        self.s.users.create("=HYPERLINK(\"http://x\")", PW, "customer", "+1@evil.example")
        self.s.users.create("@SUM(A1)", PW, "customer", "\tsneaky@example.com")
        self.s.users.create("carol", PW, "customer", "-carol@example.com")
        self.s.users.create("dave", PW, "customer", "\rdave@example.com")
        self.s.catalog.add("-X1", "Dash product", 100)
        self.s.inventory.receive("-X1", 5)
        self.s.orders.place("=HYPERLINK(\"http://x\")", {"TEA-1": 1}, "tok")
        self.s.orders.place("@SUM(A1)", {"TEA-1": 1}, "tok")
        self.s.orders.place("carol", {"-X1": 1, "TEA-1": 1}, "tok")
        self.s.orders.place("dave", {"MUG-1": 1}, "tok")
        r = rows(orders_export_csv(self.s.orders, self.s.users))
        self.assertEqual(r[1][1:3], ["'=HYPERLINK(\"http://x\")", "'+1@evil.example"])
        self.assertEqual(r[2][1:3], ["'@SUM(A1)", "'\tsneaky@example.com"])
        self.assertEqual(r[3][1:3], ["carol", "'-carol@example.com"])
        self.assertEqual(r[3][4], "'-X1:1;TEA-1:1")
        self.assertEqual(r[4][1:3], ["dave", "'\rdave@example.com"])
        for row in r[1:]:
            for cell in row:
                self.assertFalse(cell[:1] in ("=", "+", "-", "@", "\t", "\r"), (row, cell))

    def test_other_reports_unchanged_and_no_side_effects(self):
        self.s.users.create("=bad", PW, "customer", "bad@example.com")
        a = self.s.orders.place("=bad", {"TEA-1": 1}, "tok")
        self.s.orders.place("ann", {"MUG-1": 1}, "tok")
        self.s.orders.cancel(a["id"])
        csv_before, sum_before = orders_csv(self.s.orders), sales_summary(self.s.orders)
        snapshot = self.s.orders.all()
        n = len(self.s.events.events)
        orders_export_csv(self.s.orders, self.s.users)
        self.assertEqual(len(self.s.events.events), n)
        self.assertEqual(self.s.orders.all(), snapshot)
        self.assertEqual(orders_csv(self.s.orders), csv_before)
        self.assertEqual(orders_csv(self.s.orders).splitlines(),
                         ["id,customer,status,total", "O00001,=bad,cancelled,$15.00",
                          "O00002,ann,paid,$9.60"])
        self.assertEqual(sales_summary(self.s.orders), sum_before)

    def test_handler(self):
        self.s.orders.place("ann", {"TEA-1": 1}, "tok")
        self.assertEqual(self.s.api.export_orders(login(self.s, "ann"), {})[0], 403)
        code, body = self.s.api.export_orders(login(self.s, "root"), {})
        self.assertEqual(code, 200)
        self.assertEqual(body["csv"], orders_export_csv(self.s.orders, self.s.users))
        perms = dict(auth.ROLE_PERMISSIONS)
        perms["analyst"] = {"report:view"}
        perms["admin"] = perms["admin"] - {"report:view"}
        with mock.patch.dict(auth.ROLE_PERMISSIONS, perms):
            self.assertEqual(self.s.api.export_orders({"username": "x", "role": "analyst"}, {})[0], 200)
            self.assertEqual(self.s.api.export_orders(login(self.s, "root"), {})[0], 403)
