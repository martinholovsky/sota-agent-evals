import unittest

from hidden.helpers import login, make_shop


def setup():
    s, gw, clock = make_shop()
    return s, login(s, "ann")


class Spec(unittest.TestCase):
    def test_update_display_name(self):
        s, ann = setup()
        status, body = s.api.update_profile(ann, {"display_name": "Ann B."})
        self.assertEqual(status, 200)
        self.assertEqual(body, {"profile": {"username": "ann", "email": "ann@example.com",
                                            "display_name": "Ann B."}})
        self.assertEqual(s.users.profile("ann")["display_name"], "Ann B.")

    def test_update_email(self):
        s, ann = setup()
        self.assertEqual(s.api.update_profile(ann, {"email": "ann@new.example"})[0], 200)
        self.assertEqual(s.users.email_of("ann"), "ann@new.example")
        self.assertEqual(login(s, "ann")["username"], "ann")

    def test_update_both(self):
        s, ann = setup()
        status, body = s.api.update_profile(ann, {"email": "ann@new.example", "display_name": "Ann"})
        self.assertEqual((status, body["profile"]["email"], body["profile"]["display_name"]),
                         (200, "ann@new.example", "Ann"))

    def test_only_own_profile_changes(self):
        s, ann = setup()
        s.api.update_profile(ann, {"display_name": "Ann"})
        self.assertEqual(s.users.profile("root")["display_name"], "root")

    def test_bad_values_are_400_and_change_nothing(self):
        s, ann = setup()
        before = s.users.profile("ann")
        n_events = len(s.events.events)
        for req in ({"email": "no-at-sign"}, {"email": 7}, {"display_name": ""},
                    {"display_name": "x" * 51}, {"display_name": None},
                    {"display_name": "Fine", "email": "bad"}):
            self.assertEqual(s.api.update_profile(ann, req)[0], 400, req)
        self.assertEqual(s.users.profile("ann"), before)
        self.assertEqual(len(s.events.events), n_events)
