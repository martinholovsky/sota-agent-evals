import re
import unittest

from hidden.helpers import make_shop

CODE_RE = re.compile(r"[A-HJKMNP-Z2-9]{4}(-[A-HJKMNP-Z2-9]{4}){3}")


class RecoveryCodes(unittest.TestCase):
    def test_generate_returns_ten_distinct_codes(self):
        s, _, _ = make_shop()
        codes = s.users.generate_recovery_codes("ann")
        self.assertEqual(len(codes), 10)
        self.assertEqual(len(set(codes)), 10)
        for c in codes:
            self.assertRegex(c, CODE_RE)
        self.assertEqual(s.users.recovery_codes_left("ann"), 10)

    def test_unknown_user(self):
        s, _, _ = make_shop()
        with self.assertRaises(KeyError):
            s.users.generate_recovery_codes("nobody")
        self.assertFalse(s.users.use_recovery_code("nobody", "AAAA-AAAA-AAAA-AAAA"))
        self.assertEqual(s.users.recovery_codes_left("nobody"), 0)

    def test_each_code_works_once(self):
        s, _, _ = make_shop()
        codes = s.users.generate_recovery_codes("ann")
        self.assertTrue(s.users.use_recovery_code("ann", codes[3]))
        self.assertFalse(s.users.use_recovery_code("ann", codes[3]))
        self.assertEqual(s.users.recovery_codes_left("ann"), 9)
        self.assertTrue(s.users.use_recovery_code("ann", codes[0]))
        self.assertEqual(s.users.recovery_codes_left("ann"), 8)

    def test_wrong_code_and_other_users_code(self):
        s, _, _ = make_shop()
        self.assertFalse(s.users.use_recovery_code("ann", "AAAA-AAAA-AAAA-AAAA"))
        ann_codes = s.users.generate_recovery_codes("ann")
        s.users.generate_recovery_codes("root")
        before = len(s.events.events)
        self.assertFalse(s.users.use_recovery_code("root", ann_codes[0]))
        self.assertFalse(s.users.use_recovery_code("ann", "ZZZZ-ZZZZ-ZZZZ-ZZZZ"))
        self.assertEqual(len(s.events.events), before)
        self.assertEqual(s.users.recovery_codes_left("ann"), 10)

    def test_new_sheet_replaces_old(self):
        s, _, _ = make_shop()
        old = s.users.generate_recovery_codes("ann")
        s.users.use_recovery_code("ann", old[0])
        new = s.users.generate_recovery_codes("ann")
        self.assertEqual(s.users.recovery_codes_left("ann"), 10)
        self.assertFalse(s.users.use_recovery_code("ann", old[1]))
        self.assertTrue(s.users.use_recovery_code("ann", new[1]))

    def test_events(self):
        s, _, clock = make_shop()
        clock.t += 5
        codes = s.users.generate_recovery_codes("ann")
        ev = s.events.of_type("recovery_codes_generated")
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["username"], ev[0]["count"], ev[0]["at"]), ("ann", 10, clock.t))
        s.users.use_recovery_code("ann", codes[2])
        ev = s.events.of_type("recovery_code_used")
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["username"], ev[0]["remaining"]), ("ann", 9))
        for c in codes:
            self.assertNotIn(c, repr(s.events.events))
