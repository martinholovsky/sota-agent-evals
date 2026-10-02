import unittest
from src.config import deep_merge


class T(unittest.TestCase):
    def test_merge(self):
        self.assertEqual(deep_merge({"a": 1}, {"b": 2}), {"a": 1, "b": 2})
