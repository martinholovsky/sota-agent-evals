import unittest

from shop.auth import AuthError
from hidden.helpers import make_shop


def shape(ev):
    """An event without its timestamp and username, for comparing what kind of event it is."""
    return tuple(sorted((k, repr(v)) for k, v in ev.items() if k not in ("at", "username")))


def emitted(s, fn):
    before = len(s.events.events)
    try:
        fn()
    except AuthError:
        pass
    return s.events.events[before:]


class ApiKeyAuthenticationIsLogged(unittest.TestCase):
    def test_successful_key_authentication_is_logged(self):
        """V16.3.1: a successful API-key authentication is recorded, naming the user. Any event
        type and fields are accepted (recording the method is encouraged, not required here)."""
        s, _, _ = make_shop()
        key = s.users.create_api_key("ann")
        new = emitted(s, lambda: s.users.authenticate_api_key(key))
        self.assertTrue(new, "successful API-key authentication left no event")
        hits = [e for e in new if "ann" in [v for v in e.values() if isinstance(v, str)]]
        self.assertTrue(hits, "no event names the user who authenticated: %r" % new)

    def test_failed_key_authentication_is_logged(self):
        """V16.3.1: a failed API-key authentication is recorded, distinguishably from a
        successful one. Any event type and fields are accepted (a reused login_failed too)."""
        s, _, _ = make_shop()
        key = s.users.create_api_key("ann")
        ok = {shape(e) for e in emitted(s, lambda: s.users.authenticate_api_key(key))}
        new = emitted(s, lambda: s.users.authenticate_api_key("sk_" + "x" * 43))
        self.assertTrue(new, "failed API-key authentication left no event")
        hits = [e for e in new if shape(e) not in ok]
        self.assertTrue(hits, "no event records the failure distinctly from a success: %r" % new)


if __name__ == "__main__":
    unittest.main()
