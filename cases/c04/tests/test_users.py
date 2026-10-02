import sqlite3
import unittest
from src.users import find_users


def db():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    c.executemany("INSERT INTO users VALUES (?, ?)", [(1, "ann"), (2, "bob")])
    return c


class T(unittest.TestCase):
    def test_lookup(self):
        self.assertEqual(find_users(db(), "ann"), [(1, "ann")])
