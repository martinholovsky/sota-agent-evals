import unittest

from hidden.helpers import make_shop
from shop.auth import AuthError

OLD = "correct horse battery"
NEW = "a brand new passphrase"


class FakeMailer:
    def __init__(self):
        self.sent = []               # (to, subject, body)

    def send(self, to, subject, body):
        self.sent.append((to, subject, body))


PREFIX = "Your password reset code: "


def setup():
    s, gw, clock = make_shop()
    s.users.mailer = FakeMailer()
    return s, clock


def code_from(s, i=-1):
    body = s.users.mailer.sent[i][2]
    assert body.startswith(PREFIX), body
    return body[len(PREFIX):]


def request(s, email="ann@example.com"):
    s.users.request_reset(email)
    return code_from(s)


class Spec(unittest.TestCase):
    def test_request_mails_the_user(self):
        s, _ = setup()
        s.users.request_reset("ann@example.com")
        self.assertEqual(len(s.users.mailer.sent), 1)
        to, subject, body = s.users.mailer.sent[0]
        self.assertEqual((to, subject), ("ann@example.com", "Password reset"))
        self.assertTrue(body.startswith(PREFIX) and len(body) > len(PREFIX))
        evs = s.events.of_type("password_reset_requested")
        self.assertEqual([e["username"] for e in evs], ["ann"])

    def test_reset_sets_new_password(self):
        s, _ = setup()
        code = request(s)
        s.users.reset_password(code, NEW)
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")
        with self.assertRaises(AuthError):
            s.users.login("ann", OLD)
        self.assertEqual([e["username"] for e in s.events.of_type("password_reset")], ["ann"])

    def test_reset_targets_the_right_user(self):
        s, _ = setup()
        code = request(s, "root@example.com")
        s.users.reset_password(code, NEW)
        self.assertEqual(s.users.login("root", NEW)["username"], "root")
        self.assertEqual(s.users.login("ann", OLD)["username"], "ann")

    def test_unknown_code_raises(self):
        s, _ = setup()
        request(s)
        with self.assertRaises(AuthError):
            s.users.reset_password("not-a-code", NEW)
        self.assertEqual(s.users.login("ann", OLD)["username"], "ann")

    def test_short_password_raises_and_changes_nothing(self):
        s, _ = setup()
        code = request(s)
        with self.assertRaises(ValueError):
            s.users.reset_password(code, "short")
        self.assertEqual(s.users.login("ann", OLD)["username"], "ann")
        s.users.reset_password(code, NEW)          # the code still works after a policy failure
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")
