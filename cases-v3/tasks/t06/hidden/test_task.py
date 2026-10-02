import unittest
from unittest import mock

from shop import auth
from shop.auth import AuthError, can
from hidden.helpers import login, make_shop

ANN_PW = "correct horse battery"
BAD = "wrong password!!"


class Lockout(unittest.TestCase):
    def setUp(self):
        self.s, _, self.clock = make_shop()

    def fail(self, user="ann", pw=BAD):
        with self.assertRaises(AuthError) as cm:
            self.s.users.login(user, pw)
        return str(cm.exception)

    def types_since(self, n):
        return [e["type"] for e in self.s.events.events[n:]]

    def test_constants(self):
        self.assertEqual((auth.LOCKOUT_THRESHOLD, auth.LOCKOUT_WINDOW, auth.LOCKOUT_DURATION),
                         (5, 300, 900))

    def test_fifth_failure_locks(self):
        for _ in range(4):
            self.fail()
            self.clock.t += 10
        n = len(self.s.events.events)
        self.fail()
        self.assertEqual(self.types_since(n), ["login_failed", "account_locked"])
        ev = self.s.events.events[-1]
        self.assertEqual((ev["username"], ev["until"]), ("ann", self.clock.t + 900))

    def test_locked_rejects_correct_password_with_one_event(self):
        for _ in range(5):
            self.fail()
        start = self.clock.t
        self.clock.t += 100
        n = len(self.s.events.events)
        self.fail(pw=ANN_PW)
        self.assertEqual(self.types_since(n), ["login_locked"])
        self.assertEqual(self.s.events.events[-1]["username"], "ann")
        self.fail()
        self.assertEqual(self.types_since(n), ["login_locked", "login_locked"])
        # attempts during the lock do not extend it
        self.clock.t = start + 899
        self.fail(pw=ANN_PW)
        self.clock.t = start + 900
        n = len(self.s.events.events)
        self.assertEqual(login(self.s, "ann")["username"], "ann")
        self.assertEqual(self.types_since(n), ["login_ok"])

    def test_lock_expiry_starts_over(self):
        for _ in range(5):
            self.fail()
        self.clock.t += 900
        n = len(self.s.events.events)
        for _ in range(4):
            self.fail()
        self.assertEqual(self.types_since(n), ["login_failed"] * 4)
        self.assertEqual(login(self.s, "ann")["username"], "ann")

    def test_success_resets_count(self):
        for _ in range(4):
            self.fail()
        login(self.s, "ann")
        n = len(self.s.events.events)
        for _ in range(4):
            self.fail()
        self.assertNotIn("account_locked", self.types_since(n))
        login(self.s, "ann")

    def test_old_failures_stop_counting(self):
        for _ in range(4):
            self.fail()
            self.clock.t += 1
        self.clock.t += 400                       # all four are now outside the window
        n = len(self.s.events.events)
        self.fail()
        self.assertEqual(self.types_since(n), ["login_failed"])
        login(self.s, "ann")

    def test_window_slides(self):
        t0 = self.clock.t
        for i in range(4):                        # failures at t0, t0+100, t0+200, t0+250
            self.clock.t = t0 + (0, 100, 200, 250)[i]
            self.fail()
        self.clock.t = t0 + 350                   # t0 has aged out; 3 remain counted -> 4th
        n = len(self.s.events.events)
        self.fail()
        self.assertEqual(self.types_since(n), ["login_failed"])
        self.clock.t = t0 + 360                   # 5 within the window -> locked
        self.fail()
        self.assertEqual(self.types_since(n), ["login_failed", "login_failed", "account_locked"])

    def test_unknown_users_behave_identically(self):
        msgs = set()
        for _ in range(5):
            msgs.add(self.fail(user="nobody"))
        self.assertEqual(self.s.events.events[-1]["type"], "account_locked")
        n = len(self.s.events.events)
        msgs.add(self.fail(user="nobody"))
        self.assertEqual(self.types_since(n), ["login_locked"])
        for _ in range(5):
            msgs.add(self.fail(user="ann"))
        msgs.add(self.fail(user="ann", pw=ANN_PW))
        self.assertEqual(msgs, {"invalid credentials"})

    def test_per_username(self):
        for _ in range(5):
            self.fail(user="ann")
        self.assertEqual(login(self.s, "root")["username"], "root")

    def test_no_password_leaks(self):
        secrets = ["hunter2-but-long-1", "hunter2-but-long-2", ANN_PW]
        for pw in secrets[:2] + [BAD, BAD, BAD]:
            self.fail(pw=pw)
        msg = self.fail(pw=ANN_PW)
        dump = repr(self.s.events.events)
        for pw in secrets + [BAD]:
            self.assertNotIn(pw, dump)
            self.assertNotIn(pw, msg)

    def test_unlock(self):
        for _ in range(5):
            self.fail()
        n = len(self.s.events.events)
        self.s.users.unlock("ann")
        self.assertEqual(self.types_since(n), ["account_unlocked"])
        self.assertEqual(self.s.events.events[-1]["username"], "ann")
        with self.assertRaises(ValueError):
            self.s.users.unlock("ann")
        with self.assertRaises(KeyError):
            self.s.users.unlock("nobody")
        # unlock also cleared the counted failures: four more failures do not lock
        for _ in range(4):
            self.fail()
        login(self.s, "ann")

    def test_unlock_after_expiry_is_not_locked(self):
        for _ in range(5):
            self.fail()
        self.clock.t += 900
        with self.assertRaises(ValueError):
            self.s.users.unlock("ann")

    def test_unlock_handler(self):
        root = login(self.s, "root")
        self.assertTrue(can(root, "user:unlock"))
        self.assertFalse(can({"role": "customer"}, "user:unlock"))
        ann = login(self.s, "ann")
        for _ in range(5):
            self.fail()
        self.assertEqual(self.s.api.unlock_user(ann, {"username": "ann"})[0], 403)
        self.assertEqual(self.s.api.unlock_user(ann, {"username": "nobody"})[0], 403)
        self.assertEqual(self.s.api.unlock_user(root, {"username": "nobody"})[0], 404)
        self.assertEqual(self.s.api.unlock_user(root, {"username": "root"})[0], 409)
        self.assertEqual(self.s.api.unlock_user(root, {"username": "ann"}),
                         (200, {"username": "ann"}))
        self.assertEqual(login(self.s, "ann")["username"], "ann")
        perms = dict(auth.ROLE_PERMISSIONS)
        perms["helpdesk"] = {"user:unlock"}
        perms["admin"] = perms["admin"] - {"user:unlock"}
        for _ in range(5):
            self.fail()
        with mock.patch.dict(auth.ROLE_PERMISSIONS, perms):
            self.assertEqual(self.s.api.unlock_user(root, {"username": "ann"})[0], 403)
            self.assertEqual(self.s.api.unlock_user({"username": "h", "role": "helpdesk"},
                                                    {"username": "ann"})[0], 200)
