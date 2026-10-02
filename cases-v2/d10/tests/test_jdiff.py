import unittest
from src.jdiff import diff


class T(unittest.TestCase):
    def test_add(self):
        self.assertEqual(diff({}, {"a": 1}), [{"op": "add", "path": "/a", "value": 1}])
