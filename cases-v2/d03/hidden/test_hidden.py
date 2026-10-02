import unittest
from src.allocate import allocate


class H(unittest.TestCase):
    def test_sum_preserved(self):
        for total, ratios in [(100, [1, 1, 1]), (7, [1, 2, 3]), (1, [5, 5]), (999, [0.3, 0.7])]:
            self.assertEqual(sum(allocate(total, ratios)), total, (total, ratios))

    def test_largest_remainder_and_ties(self):
        self.assertEqual(allocate(100, [1, 1, 1]), [34, 33, 33])
        self.assertEqual(allocate(10, [1, 2]), [3, 7])
        self.assertEqual(allocate(7, [1, 2, 3]), [1, 2, 4])

    def test_zero_ratio(self):
        self.assertEqual(allocate(10, [0, 1]), [0, 10])

    def test_negative(self):
        self.assertEqual(allocate(-100, [1, 1, 1]), [-34, -33, -33])

    def test_invalid(self):
        for r in [[], [0, 0], [-1, 2]]:
            with self.assertRaises(ValueError, msg=r):
                allocate(10, r)
