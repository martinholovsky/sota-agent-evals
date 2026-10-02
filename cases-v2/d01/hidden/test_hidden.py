import unittest
from src.semver import compare


class H(unittest.TestCase):
    def test_core(self):
        self.assertEqual(compare("2.0.0", "1.99.99"), 1)
        self.assertEqual(compare("1.0.0", "1.0.0"), 0)

    def test_prerelease_lower(self):
        self.assertEqual(compare("1.0.0-alpha", "1.0.0"), -1)

    def test_spec_chain(self):
        chain = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
                 "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
        for lo, hi in zip(chain, chain[1:]):
            self.assertEqual(compare(lo, hi), -1, (lo, hi))
            self.assertEqual(compare(hi, lo), 1, (hi, lo))

    def test_build_ignored(self):
        self.assertEqual(compare("1.0.0+abc", "1.0.0+xyz"), 0)
        self.assertEqual(compare("1.0.0-rc.1+b1", "1.0.0-rc.1"), 0)

    def test_invalid(self):
        for bad in ["1.0", "01.0.0", "1.0.0-", "a.b.c", "1.0.0.0", ""]:
            with self.assertRaises(ValueError, msg=bad):
                compare(bad, "1.0.0")
