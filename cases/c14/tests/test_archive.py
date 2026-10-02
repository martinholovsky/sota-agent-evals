import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "archive.sh")


class T(unittest.TestCase):
    def test_simple(self):
        d = tempfile.mkdtemp(); dest = os.path.join(d, "out"); os.mkdir(dest)
        f = os.path.join(d, "a.txt"); open(f, "w").write("x")
        r = subprocess.run(["sh", SCRIPT, dest, f], capture_output=True, text=True)
        self.assertIn("archived 1", r.stdout)
