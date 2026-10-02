import unittest
from src.paths import safe_join


class H(unittest.TestCase):
    def test_normalise(self):
        self.assertEqual(safe_join("/srv/www", "a//./b/../c.txt"), "/srv/www/a/c.txt")
        self.assertEqual(safe_join("/srv/www", "/"), "/srv/www")
        self.assertEqual(safe_join("/srv/www", "a/b/"), "/srv/www/a/b")

    def test_escape(self):
        for p in ["../etc/passwd", "/a/../../x", "%2e%2e/secret", "a/%2E%2E/%2e%2e/x"]:
            with self.assertRaises(ValueError, msg=p):
                safe_join("/srv/www", p)

    def test_bad_chars(self):
        for p in ["a%00b", "a\\b", "a%5cb"]:
            with self.assertRaises(ValueError, msg=p):
                safe_join("/srv/www", p)

    def test_decoded_spaces(self):
        self.assertEqual(safe_join("/srv/www", "my%20file.txt"), "/srv/www/my file.txt")
