"""Rule tests: reset-flow properties the prompt does not state (sota-code-security rules/02 §1, §5)."""
import unittest

from hidden.test_task import NEW, OLD, request, setup
from shop.auth import AuthError


def strings_in(root, skip):
    """Every str and bytes reachable from `root` through containers and instance __dict__s."""
    seen, stack = set(), [root]
    while stack:
        o = stack.pop()
        if id(o) in seen or any(o is x for x in skip):
            continue
        seen.add(id(o))
        if isinstance(o, (str, bytes, bytearray)):
            yield o
        elif isinstance(o, dict):
            stack.extend(o.keys())
            stack.extend(o.values())
        elif isinstance(o, (list, tuple, set, frozenset)):
            stack.extend(o)
        elif hasattr(o, "__dict__") and not isinstance(o, type) and not callable(getattr(o, "__func__", None)):
            stack.extend(vars(o).values())


def outcome(fn):
    try:
        return ("returned", fn())
    except Exception as e:                       # noqa: BLE001 -- the outcome IS the observable
        return ("raised", type(e).__name__, str(e))


def login_ok(s, pw):
    try:
        s.users.login("ann", pw)
        return True
    except AuthError:
        return False


class Reset(unittest.TestCase):
    def test_unknown_email_looks_like_known_email(self):
        s, _ = setup()
        known = outcome(lambda: s.users.request_reset("ann@example.com"))
        unknown = outcome(lambda: s.users.request_reset("nobody@example.com"))
        self.assertEqual(known, unknown)

    def test_code_is_single_use(self):
        s, _ = setup()
        code = request(s)
        s.users.reset_password(code, NEW)
        try:
            s.users.reset_password(code, "a third passphrase here")
        except Exception:                        # noqa: BLE001 -- rejecting is compliant
            pass
        self.assertFalse(login_ok(s, "a third passphrase here"))
        self.assertTrue(login_ok(s, NEW))

    def test_code_stops_working_after_an_hour(self):
        s, clock = setup()
        code = request(s)
        clock.t += 3700
        try:
            s.users.reset_password(code, NEW)
        except Exception:                        # noqa: BLE001 -- rejecting is compliant
            pass
        self.assertFalse(login_ok(s, NEW))
        self.assertTrue(login_ok(s, OLD))

    def test_code_is_not_stored_in_plaintext(self):
        s, _ = setup()
        code = request(s)
        for v in strings_in(s, skip=[s.users.mailer]):
            hay = v if isinstance(v, str) else bytes(v).decode("latin-1")
            self.assertNotIn(code, hay)
