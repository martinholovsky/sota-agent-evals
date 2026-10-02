import unittest
from src.sku import is_valid_sku


class T(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(is_valid_sku("AB-12-C"))
