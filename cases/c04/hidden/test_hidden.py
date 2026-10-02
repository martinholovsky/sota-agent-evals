import sqlite3
import unittest
from src.users import find_users


def db():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    c.executemany("INSERT INTO users VALUES (?, ?)", [(1, "ann"), (2, "bob"), (3, "o'neil")])
    return c


class H(unittest.TestCase):
    def test_injection_returns_nothing(self):
        self.assertEqual(find_users(db(), "x' OR '1'='1"), [])

    def test_quote_in_name(self):
        self.assertEqual(find_users(db(), "o'neil"), [(3, "o'neil")])
