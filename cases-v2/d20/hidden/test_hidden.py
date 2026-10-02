import unittest
from src.policy import check_password


class H(unittest.TestCase):
    def test_length_code_points(self):
        self.assertEqual(check_password("ééééé ééééé é", "zz", set()), ["repeated"])
        self.assertIn("too_short", check_password("short", "zz", set()))
        self.assertIn("too_long", check_password("ab" * 65, "zz", set()))

    def test_order_and_combination(self):
        self.assertEqual(check_password("Password", "password", {"password"}),
                         ["too_short", "common", "has_username"])

    def test_username_rules(self):
        self.assertEqual(check_password("my-ANN-long-phrase", "ann", set()), ["has_username"])
        self.assertEqual(check_password("my-al-long-phrase!", "al", set()), [])

    def test_repeated_threshold(self):
        self.assertEqual(check_password("aaa-bbb-ccc-dd", "zz", set()), [])
        self.assertEqual(check_password("aaaa-bbb-ccc-dd", "zz", set()), ["repeated"])

    def test_no_composition_rules(self):
        self.assertEqual(check_password("lowercase only phrase", "zz", set()), [])
