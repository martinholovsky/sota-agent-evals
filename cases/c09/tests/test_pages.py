import unittest
from src.pages import paginate


class T(unittest.TestCase):
    def test_first_page(self):
        self.assertEqual(paginate(list(range(10)), 1, 3)["items"], [0, 1, 2])
