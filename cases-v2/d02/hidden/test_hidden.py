import unittest
from src.intervals import merge


class H(unittest.TestCase):
    def test_touching(self):
        self.assertEqual(merge([(3, 5), (1, 3)]), [(1, 5)])

    def test_contained_and_unsorted(self):
        self.assertEqual(merge([(10, 12), (1, 9), (2, 3)]), [(1, 9), (10, 12)])

    def test_empty_ranges_dropped(self):
        self.assertEqual(merge([(2, 2), (5, 6)]), [(5, 6)])
        self.assertEqual(merge([]), [])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            merge([(5, 1)])

    def test_input_untouched(self):
        src = [(5, 6), (1, 2)]
        merge(src)
        self.assertEqual(src, [(5, 6), (1, 2)])
