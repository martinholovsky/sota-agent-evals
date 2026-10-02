import unittest
from src.report import coverage_line, success_line


class T(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(success_line(1, 4), "success: 25.0%")
        self.assertEqual(coverage_line(1, 2), "coverage: 50.0%")
