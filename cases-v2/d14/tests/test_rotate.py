import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "rotate.sh")


class T(unittest.TestCase):
    def test_usage(self):
        r = subprocess.run(["sh", SCRIPT], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
