import unittest
from src.paths import safe_join


class T(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(safe_join("/srv/www", "/a/b.html"), "/srv/www/a/b.html")
