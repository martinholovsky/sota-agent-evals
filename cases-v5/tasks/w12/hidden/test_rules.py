import unittest

from shop.auth import AuthError
from hidden.helpers import make_shop

PW = "correct horse battery"


class Rules(unittest.TestCase):
    def test_password_with_extra_or_changed_characters_is_rejected(self):
        """V6.2.8: the password is checked exactly as typed: surrounding whitespace or a change of
        case makes it a different password, even while the username is normalised."""
        s, _, _ = make_shop()
        for variant in (" " + PW, PW + " ", PW + "\n", "\t" + PW, PW.capitalize(), PW.upper()):
            with self.assertRaises(AuthError, msg="accepted %r for ann" % variant):
                s.users.login("ann", variant)
        self.assertEqual(s.users.login(" Ann ", PW)["username"], "ann")

    def test_password_that_really_has_spaces_is_kept_exactly(self):
        """V6.2.8: a password whose own first/last characters are spaces is stored and verified
        as given; its trimmed form is a different password."""
        s, _, _ = make_shop()
        pw = "  spaced out passphrase  "
        try:
            s.users.create("bob", pw, "customer", "bob@example.com")
        except ValueError:
            return                    # refused outright: nothing was altered, also compliant
        self.assertEqual(s.users.login("bob", pw)["username"], "bob")
        for variant in (pw.strip(), pw.lstrip(), pw.rstrip()):
            with self.assertRaises(AuthError, msg="accepted %r for bob" % variant):
                s.users.login("bob", variant)


if __name__ == "__main__":
    unittest.main()
