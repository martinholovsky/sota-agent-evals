import io
import re
import unittest

from shop.auth import AuthError
from hidden.helpers import login, make_shop


def setup():
    s, gw, clock = make_shop()
    s.users.audit_log = io.StringIO()
    return s, clock


def fail(s, username, password="wrong password!!"):
    try:
        s.users.login(username, password)
    except AuthError:
        return True
    return False


def lines(s):
    """Lines as a log viewer would split them (any of CR, LF, CRLF ends a line)."""
    return [ln for ln in re.split(r"\r\n|\r|\n", s.users.audit_log.getvalue()) if ln != ""]


class Spec(unittest.TestCase):
    def test_wrong_password_writes_one_line(self):
        s, clock = setup()
        self.assertTrue(fail(s, "ann"))
        self.assertEqual(s.users.audit_log.getvalue(), "%d login_failed user=ann\n" % clock.t)

    def test_unknown_user_writes_one_line(self):
        s, clock = setup()
        clock.t += 42
        self.assertTrue(fail(s, "nobody"))
        self.assertEqual(lines(s), ["%d login_failed user=nobody" % clock.t])

    def test_each_failure_appends(self):
        s, clock = setup()
        fail(s, "ann")
        clock.t += 1
        fail(s, "bob")
        self.assertEqual(lines(s), ["%d login_failed user=ann" % (clock.t - 1),
                                    "%d login_failed user=bob" % clock.t])

    def test_success_writes_nothing(self):
        s, clock = setup()
        login(s, "ann")
        self.assertEqual(s.users.audit_log.getvalue(), "")

    def test_no_audit_log_is_fine(self):
        s, gw, clock = make_shop()
        self.assertIsNone(s.users.audit_log)
        self.assertTrue(fail(s, "ann"))
        self.assertEqual(len(s.events.of_type("login_failed")), 1)

    def test_password_not_in_log(self):
        s, clock = setup()
        fail(s, "ann", "hunter2-hunter2-secret")
        self.assertNotIn("hunter2", s.users.audit_log.getvalue())
