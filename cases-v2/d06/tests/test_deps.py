import unittest
from src.deps import build_order


class T(unittest.TestCase):
    def test_chain(self):
        self.assertEqual(build_order({"app": ["lib"], "lib": []}), ["lib", "app"])
