import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "archive.sh")


class H(unittest.TestCase):
    def run_it(self, names):
        d = tempfile.mkdtemp(); dest = os.path.join(d, "out dir"); os.mkdir(dest)
        paths = []
        for n in names:
            p = os.path.join(d, n); open(p, "w").write(n); paths.append(p)
        r = subprocess.run(["sh", SCRIPT, dest] + paths, capture_output=True, text=True)
        return r, dest

    def test_spaces_and_globs(self):
        names = ["my file.txt", "*.txt", "-n.txt"]
        r, dest = self.run_it(names)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(os.listdir(dest)), sorted(names))
        self.assertIn("archived 3", r.stdout)

    def test_missing_file_fails(self):
        d = tempfile.mkdtemp()
        r = subprocess.run(["sh", SCRIPT, d, os.path.join(d, "nope.txt")], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("archived 1", r.stdout)
