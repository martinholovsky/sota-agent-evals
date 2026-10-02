import unittest
from src.conf import parse_config


class T(unittest.TestCase):
    def test_one(self):
        self.assertEqual(parse_config("[db]\nhost = x\n"), {"db": {"host": "x"}})
