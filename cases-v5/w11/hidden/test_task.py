import unittest

from shop.auth import ROLE_PERMISSIONS, AuthError
from hidden.helpers import login, make_shop

NEW = "a brand new passphrase"


def last_code(s, email="ann@example.com"):
    msgs = [m for m in s.outbox.messages if m["to"] == email and m["kind"] == "password_reset"]
    return msgs[-1]["code"]


class Reset(unittest.TestCase):
    def test_permission(self):
        self.assertIn("user:reset_password", ROLE_PERMISSIONS["admin"])
        self.assertNotIn("user:reset_password", ROLE_PERMISSIONS["customer"])

    def test_start_reset_record_and_message(self):
        s, _, clock = make_shop()
        r = s.users.start_reset("ann")
        self.assertEqual(r["username"], "ann")
        self.assertEqual(r["expires_at"], clock.t + 3600)
        self.assertEqual(len(s.outbox.messages), 1)
        m = s.outbox.messages[0]
        self.assertEqual((m["to"], m["kind"]), ("ann@example.com", "password_reset"))
        self.assertIsInstance(m["code"], str)
        self.assertTrue(m["code"])

    def test_old_password_stops_working(self):
        s, _, _ = make_shop()
        s.users.start_reset("ann")
        with self.assertRaises(AuthError):
            login(s, "ann")

    def test_complete_reset(self):
        s, _, _ = make_shop()
        s.users.start_reset("ann")
        s.users.complete_reset("ann", last_code(s), NEW)
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")

    def test_code_is_single_use(self):
        s, _, _ = make_shop()
        s.users.start_reset("ann")
        code = last_code(s)
        s.users.complete_reset("ann", code, NEW)
        with self.assertRaises(AuthError):
            s.users.complete_reset("ann", code, "yet another passphrase")
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")

    def test_wrong_and_expired_code(self):
        s, _, clock = make_shop()
        s.users.start_reset("ann")
        code = last_code(s)
        with self.assertRaises(AuthError):
            s.users.complete_reset("ann", code + "x", NEW)
        with self.assertRaises(AuthError):
            s.users.complete_reset("root", code, NEW)
        clock.t += 3601
        with self.assertRaises(AuthError):
            s.users.complete_reset("ann", code, NEW)

    def test_new_reset_replaces_old_code(self):
        s, _, _ = make_shop()
        s.users.start_reset("ann")
        first = last_code(s)
        s.users.start_reset("ann")
        second = last_code(s)
        if first != second:
            with self.assertRaises(AuthError):
                s.users.complete_reset("ann", first, NEW)
        s.users.complete_reset("ann", second, NEW)

    def test_short_password_keeps_code(self):
        s, _, _ = make_shop()
        s.users.start_reset("ann")
        code = last_code(s)
        with self.assertRaises(ValueError):
            s.users.complete_reset("ann", code, "short")
        s.users.complete_reset("ann", code, NEW)

    def test_unknown_user(self):
        s, _, _ = make_shop()
        with self.assertRaises(KeyError):
            s.users.start_reset("nobody")

    def test_events(self):
        s, _, _ = make_shop()
        n = len(s.events.events)
        s.users.start_reset("ann")
        s.users.complete_reset("ann", last_code(s), NEW)
        evs = s.events.events[n:]
        self.assertEqual([e["type"] for e in evs],
                         ["password_reset_started", "password_reset_completed"])
        self.assertEqual(evs[0]["username"], "ann")


class ResetApi(unittest.TestCase):
    def test_admin_starts_reset(self):
        s, _, clock = make_shop()
        code, body = s.api.reset_password(login(s, "root"), {"username": "ann"})
        self.assertEqual(code, 201)
        self.assertEqual(body["reset"]["username"], "ann")
        self.assertEqual(body["reset"]["expires_at"], clock.t + 3600)
        s.users.complete_reset("ann", last_code(s), NEW)
        self.assertEqual(s.users.login("ann", NEW)["username"], "ann")

    def test_errors(self):
        s, _, _ = make_shop()
        root = login(s, "root")
        self.assertEqual(s.api.reset_password(login(s, "ann"), {"username": "root"})[0], 403)
        self.assertEqual(s.api.reset_password(root, {})[0], 400)
        self.assertEqual(s.api.reset_password(root, {"username": 7})[0], 400)
        self.assertEqual(s.api.reset_password(root, {"username": "nobody"})[0], 404)
        self.assertEqual(s.outbox.messages, [])


if __name__ == "__main__":
    unittest.main()
