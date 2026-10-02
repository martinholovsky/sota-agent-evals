import unittest
from src.export import to_csv


class T(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(to_csv([["a", "b"]]), "a,b\r\n")
