import unittest
from src.text import slugify


class T(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello,  World!"), "hello-world")
