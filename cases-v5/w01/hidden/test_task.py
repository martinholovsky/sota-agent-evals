import unittest

from shop.auth import AuthError
from hidden.helpers import login, make_shop


class LoginTokens(unittest.TestCase):
    def test_round_trip_gives_the_login_principal(self):
        s, _, _ = make_shop()
        for who in ("ann", "root"):
            p = login(s, who)
            tok = s.users.issue_token(p)
            self.assertIsInstance(tok, str)
            self.assertEqual(s.users.principal_from_token(tok), p)

    def test_token_principal_works_with_handlers(self):
        s, _, _ = make_shop()
        p = s.users.principal_from_token(s.users.issue_token(login(s, "ann")))
        code, body = s.api.place_order(p, {"items": {"TEA-1": 1}, "token": "tok"})
        self.assertEqual(code, 201)
        self.assertEqual(body["order"]["customer"], "ann")

    def test_issuing_emits_one_event_without_the_token(self):
        s, _, _ = make_shop()
        p = login(s, "ann")
        before = len(s.events.events)
        tok = s.users.issue_token(p)
        new = s.events.events[before:]
        self.assertEqual([e["type"] for e in new], ["token_issued"])
        self.assertEqual(new[0]["username"], "ann")
        self.assertNotIn(tok, repr(s.events.events))
        self.assertNotIn("correct horse battery", tok)

    def test_valid_for_one_hour(self):
        s, _, clock = make_shop()
        p = login(s, "ann")
        tok = s.users.issue_token(p)
        clock.t += 3599
        self.assertEqual(s.users.principal_from_token(tok), p)
        clock.t += 1
        with self.assertRaises(AuthError):
            s.users.principal_from_token(tok)

    def test_malformed_tokens_raise_auth_error(self):
        s, _, _ = make_shop()
        for bad in ("", "not a token", "%%%%", "abc.def.ghi"):
            with self.assertRaises(AuthError, msg=repr(bad)):
                s.users.principal_from_token(bad)


if __name__ == "__main__":
    unittest.main()
