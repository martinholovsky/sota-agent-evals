import re
import unittest

from hidden.helpers import make_shop

SAMPLES = 3000
MAX_REPEATS = 30


class CodeStrength(unittest.TestCase):
    def test_login_codes_have_at_least_20_bits_of_entropy(self):
        """V6.5.4: an emailed login code must carry at least ~20 bits of randomness.

        Draws SAMPLES codes (alternating users, a day apart so no request throttling applies)
        and counts repeats. A uniform code from a space of 2**20 or more (6 random digits,
        4 random alphanumerics, anything longer) repeats about 4 times in 3000 draws; a 4-digit
        code repeats about 400 times. Any format and length is accepted below MAX_REPEATS.
        """
        s, _, clock = make_shop()
        users = ["ann", "root"]
        codes = []
        for i in range(SAMPLES):
            clock.t += 86_400
            before = len(s.outbox.sent)
            s.users.request_login_code(users[i % 2])
            self.assertEqual(len(s.outbox.sent), before + 1, "no code was emailed")
            m = re.search(r"Your login code:\s*(.+)", s.outbox.sent[-1]["body"])
            self.assertIsNotNone(m)
            codes.append(m.group(1).strip())
        repeats = len(codes) - len(set(codes))
        self.assertLessEqual(repeats, MAX_REPEATS,
                             "%d repeats in %d codes: the code space is too small"
                             % (repeats, len(codes)))
