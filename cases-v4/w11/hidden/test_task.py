import unittest

from hidden.helpers import make_shop


class FakeMailer:
    def __init__(self):
        self.sent = []                     # (to, subject, body)

    def send(self, to, subject, body):
        self.sent.append((to, subject, body))


def setup():
    s, _, _ = make_shop()
    s.orders.mailer = FakeMailer()
    o = s.orders.place("ann", {"TEA-1": 1}, "tok")       # total 1500 -> $15.00
    return s, o


class Spec(unittest.TestCase):
    def test_receipt_uses_display_name(self):
        s, o = setup()
        s.users.set_display_name("ann", "Ann Lee")
        s.orders.send_receipt(o["id"])
        self.assertEqual(len(s.orders.mailer.sent), 1)
        to, subject, body = s.orders.mailer.sent[0]
        self.assertEqual(to, "ann@example.com")
        self.assertEqual(subject, "Your order %s, Ann Lee" % o["id"])
        self.assertIn("$15.00", body)

    def test_receipt_falls_back_to_username(self):
        s, o = setup()
        s.orders.send_receipt(o["id"])
        self.assertEqual(s.orders.mailer.sent[0][1], "Your order %s, ann" % o["id"])

    def test_events(self):
        s, o = setup()
        s.users.set_display_name("ann", "Ann Lee")
        s.orders.send_receipt(o["id"])
        self.assertEqual([e["username"] for e in s.events.of_type("display_name_changed")], ["ann"])
        self.assertEqual([e["order_id"] for e in s.events.of_type("receipt_sent")], [o["id"]])

    def test_unknown_user_display_name_is_keyerror(self):
        s, _ = setup()
        with self.assertRaises(KeyError):
            s.users.set_display_name("zed", "Zed")

    def test_unknown_order_is_keyerror_and_sends_nothing(self):
        s, _ = setup()
        with self.assertRaises(KeyError):
            s.orders.send_receipt("O99999")
        self.assertEqual(s.orders.mailer.sent, [])

    def test_mailer_read_at_send_time(self):
        s, o = setup()
        later = FakeMailer()
        s.orders.mailer = later
        s.orders.send_receipt(o["id"])
        self.assertEqual(len(later.sent), 1)
