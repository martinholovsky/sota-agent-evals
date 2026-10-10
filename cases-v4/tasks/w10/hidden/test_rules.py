"""Rule tests: mass assignment the prompt does not state (sota-code-security rules/03 §2,
rules/07 §3). Rejecting the request (400) and ignoring the extra keys both comply."""
import unittest

from hidden.helpers import login
from hidden.test_task import setup
from shop.auth import AuthError, _hash, can


class MassAssignment(unittest.TestCase):
    def test_role_in_request_does_not_change_role(self):
        s, ann = setup()
        s.api.update_profile(ann, {"display_name": "Ann", "role": "admin"})
        fresh = login(s, "ann")
        self.assertEqual(fresh["role"], "customer")
        self.assertFalse(can(fresh, "order:view_any"))

    def test_credential_fields_in_request_are_not_written(self):
        s, ann = setup()
        salt = b"\x01" * 16
        s.api.update_profile(ann, {"display_name": "Ann", "salt": salt,
                                   "hash": _hash("chosen by the caller", salt)})
        with self.assertRaises(AuthError):
            s.users.login("ann", "chosen by the caller")
        self.assertEqual(login(s, "ann")["username"], "ann")
