import os
import subprocess
import sys
import tempfile
import unittest

CLI = os.path.join(os.path.dirname(__file__), "..", "src", "cli.py")


class T(unittest.TestCase):
    def test_sum(self):
        f = tempfile.mktemp(); open(f, "w").write("1 2 3")
        r = subprocess.run([sys.executable, CLI, f], capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "6.0")
