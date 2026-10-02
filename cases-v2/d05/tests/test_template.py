import unittest
from src.template import render


class T(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(render("Hi {{name}}!", {"name": "Ann"}), "Hi Ann!")
