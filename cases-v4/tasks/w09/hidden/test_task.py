import unittest

from hidden.helpers import make_shop

ANN = {"username": "ann", "password": "correct horse battery"}


def go(s, nxt=None, **over):
    req = dict(ANN, **over)
    if nxt is not None:
        req["next"] = nxt
    return s.api.login_redirect(req)


class Spec(unittest.TestCase):
    def test_success_redirects_to_next(self):
        s, _, _ = make_shop()
        self.assertEqual(go(s, "/orders/7"), (302, {"location": "/orders/7"}))

    def test_next_with_query_is_kept(self):
        s, _, _ = make_shop()
        self.assertEqual(go(s, "/orders?page=2"), (302, {"location": "/orders?page=2"}))

    def test_missing_or_empty_next_goes_home(self):
        s, _, _ = make_shop()
        self.assertEqual(go(s), (302, {"location": "/"}))
        self.assertEqual(go(s, ""), (302, {"location": "/"}))

    def test_wrong_password_is_401(self):
        s, _, _ = make_shop()
        self.assertEqual(go(s, "/orders/7", password="nope nope nope")[0], 401)

    def test_unknown_user_is_401(self):
        s, _, _ = make_shop()
        self.assertEqual(go(s, "/orders/7", username="zed")[0], 401)

    def test_login_is_recorded(self):
        s, _, _ = make_shop()
        go(s, "/orders/7")
        self.assertEqual(len(s.events.of_type("login_ok")), 1)
