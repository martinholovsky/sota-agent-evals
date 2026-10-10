import unittest

from hidden.helpers import make_shop

ANN_PW = "correct horse battery"


def setup():
    s, gw, clock = make_shop()
    return s, clock


def login(s, username, password):
    return s.api.login({"username": username, "password": password})


class Spec(unittest.TestCase):
    def test_valid_credentials(self):
        s, _ = setup()
        self.assertEqual(login(s, "ann", ANN_PW),
                         (200, {"principal": {"username": "ann", "role": "customer"}}))
        self.assertEqual(login(s, "root", "correct horse staple!")[1]["principal"]["role"], "admin")

    def test_wrong_password_is_401(self):
        s, _ = setup()
        self.assertEqual(login(s, "ann", "wrong password!!"), (401, {"error": "invalid credentials"}))

    def test_unknown_user_is_401(self):
        s, _ = setup()
        self.assertEqual(login(s, "nobody", "whatever whatever"), (401, {"error": "invalid credentials"}))

    def test_a_few_typos_then_success(self):
        s, clock = setup()
        clock.t += 300                     # a human retyping, not a burst
        self.assertEqual(login(s, "ann", "correct horse batery")[0], 401)
        clock.t += 300
        self.assertEqual(login(s, "ann", "correct hors battery")[0], 401)
        clock.t += 300
        self.assertEqual(login(s, "ann", ANN_PW)[0], 200)

    def test_bad_input_is_400(self):
        s, _ = setup()
        self.assertEqual(s.api.login({"username": "ann"})[0], 400)
        self.assertEqual(s.api.login({"password": ANN_PW})[0], 400)
        self.assertEqual(s.api.login({"username": 5, "password": ANN_PW})[0], 400)
        self.assertEqual(s.api.login({"username": "ann", "password": None})[0], 400)
