import os
import subprocess
import sys
import tempfile
import unittest

CLI = os.path.join(os.path.dirname(__file__), "..", "src", "cli.py")


def run(*args):
    return subprocess.run([sys.executable, CLI, *args], capture_output=True, text=True)


class H(unittest.TestCase):
    def test_missing_file(self):
        r = run("/nonexistent/file")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")
        self.assertTrue(r.stderr.strip())

    def test_bad_number(self):
        f = tempfile.mktemp(); open(f, "w").write("1 x")
        r = run(f)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr.strip())

    def test_no_args(self):
        self.assertNotEqual(run().returncode, 0)

    def test_success_still_zero(self):
        f = tempfile.mktemp(); open(f, "w").write("2 2")
        r = run(f)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "4.0"))
