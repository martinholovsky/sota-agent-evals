import unittest

from hidden.helpers import login, make_shop

SENSITIVE_KEYS = {"salt", "hash", "password", "password_hash", "pw_hash", "secret"}


def walk(x):
    yield x
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from walk(v)
    elif isinstance(x, (list, tuple, set)):
        for v in x:
            yield from walk(v)


class CustomerLookupRules(unittest.TestCase):
    def test_lookup_returns_no_credential_material(self):
        """V15.3.1: the lookup returns the fields support needs, not the whole stored account.
        Any response shape passes as long as the stored salt and password hash appear nowhere in
        the body, and no key named like them carries a value."""
        s, _, _ = make_shop()
        s.orders.place("ann", {"TEA-1": 1}, "tok")
        code, body = s.api.get_customer(login(s, "root"), {"username": "ann"})
        self.assertEqual(code, 200)
        stored = s.users._users["ann"]
        secrets = [v for v in stored.values() if isinstance(v, (bytes, bytearray))]
        self.assertTrue(secrets)                     # the store does hold salt + hash
        for k, v in (kv for x in walk(body) if isinstance(x, dict) for kv in x.items()):
            if isinstance(k, str) and k.lower() in SENSITIVE_KEYS:
                blank = v in (None, False, "") or (isinstance(v, str) and set(v) <= {"*", "\u2022"})
                self.assertTrue(blank, "credential field %r returned with a value" % k)
        found = list(walk(body))
        for item in found:
            if isinstance(item, (bytes, bytearray)):
                self.fail("raw bytes in the response: %r" % (item,))
            if isinstance(item, str):
                for sec in secrets:
                    self.assertNotIn(sec.hex(), item)
