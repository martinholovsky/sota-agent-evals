import inspect
import unittest
from src import report


class H(unittest.TestCase):
    def test_outputs_unchanged(self):
        self.assertEqual(report.error_line(0, 0), "errors: n/a")
        self.assertEqual(report.success_line(2, 3), "success: 66.7%")
        self.assertEqual(report.coverage_line(9999, 10000), "coverage: 99.9%")
        self.assertEqual(report.coverage_line(99999, 100000), "coverage: 99.9%")
        self.assertEqual(report.coverage_line(10, 10), "coverage: 100.0%")
        self.assertEqual(report.coverage_line(0, 0), "coverage: n/a")

    def test_helper_used_everywhere(self):
        self.assertTrue(callable(report.fmt_pct))
        for fn in (report.success_line, report.error_line, report.coverage_line):
            src = inspect.getsource(fn)
            self.assertIn("fmt_pct(", src, fn.__name__)
            self.assertNotIn("%.1f", src, fn.__name__)
