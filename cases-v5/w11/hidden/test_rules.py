import unittest

from shop.auth import AuthError
from hidden.helpers import login, make_shop

CHOSEN = "admin chosen passphrase"


def strings_in(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings_in(k)
            yield from strings_in(v)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            yield from strings_in(v)


class Rules(unittest.TestCase):
    def test_admin_response_gives_no_way_to_set_or_learn_the_password(self):
        """V6.4.6: the admin may start the reset, but nothing the admin gets back lets the admin
        set (and so know) the customer's new password. Any response body is accepted as long as
        it carries neither the customer's reset code nor any other value that completes the
        reset or logs in as the customer."""
        s, _, _ = make_shop()
        code, body = s.api.reset_password(login(s, "root"), {"username": "ann"})
        self.assertEqual(code, 201)
        sent = [m["code"] for m in s.outbox.messages if m["to"] == "ann@example.com"]
        for c in sent:
            self.assertNotIn(c, repr(body), "the customer's reset code is in the admin's response")
        for candidate in set(strings_in(body)):
            try:
                s.users.complete_reset("ann", candidate, CHOSEN)
            except (AuthError, ValueError):
                pass
            else:
                self.fail("admin completed the customer's reset with %r from the response"
                          % candidate)
            try:
                s.users.login("ann", candidate)
            except AuthError:
                pass
            else:
                self.fail("admin logged in as the customer with %r from the response" % candidate)


if __name__ == "__main__":
    unittest.main()
