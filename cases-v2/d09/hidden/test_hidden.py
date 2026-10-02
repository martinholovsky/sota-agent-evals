import unittest
from src.roman import from_roman, to_roman


class H(unittest.TestCase):
    def test_round_trip_all(self):
        for n in range(1, 4000):
            self.assertEqual(from_roman(to_roman(n)), n)

    def test_known(self):
        self.assertEqual(to_roman(1994), "MCMXCIV")
        self.assertEqual(to_roman(3999), "MMMCMXCIX")

    def test_bad_ints(self):
        for n in [0, 4000, -1, True, 2.0]:
            with self.assertRaises(ValueError, msg=n):
                to_roman(n)

    def test_non_canonical(self):
        for s in ["IIII", "IC", "VX", "MMMM", "", "iv", "XM", "IIV"]:
            with self.assertRaises(ValueError, msg=s):
                from_roman(s)
