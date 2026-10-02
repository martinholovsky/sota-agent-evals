import os
import subprocess
import tempfile
import time
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "rotate.sh")


def mk(d, names):
    for i, n in enumerate(names):
        p = os.path.join(d, n)
        open(p, "w").write(n)
        t = 1_700_000_000 + i * 100            # later in the list = newer
        os.utime(p, (t, t))


class H(unittest.TestCase):
    def test_keeps_newest(self):
        d = tempfile.mkdtemp()
        mk(d, ["b 1.tar", "b 2.tar", "b 3.tar", "b 4.tar", "notes.txt"])
        r = subprocess.run(["sh", SCRIPT, d, "2"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(os.listdir(d)), ["b 3.tar", "b 4.tar", "notes.txt"])
        self.assertEqual(sorted(r.stdout.split("\n")[:-1]), sorted(["removed " + os.path.join(d, "b 1.tar"), "removed " + os.path.join(d, "b 2.tar")]))

    def test_dry_run(self):
        d = tempfile.mkdtemp()
        mk(d, ["a.tar", "b.tar", "c.tar"])
        r = subprocess.run(["sh", SCRIPT, "--dry-run", d, "1"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(os.listdir(d)), 3)
        self.assertEqual(r.stdout.count("would remove "), 2)

    def test_errors(self):
        d = tempfile.mkdtemp()
        for args in [[d, "x"], [d, "-1"], [os.path.join(d, "missing"), "2"], [d]]:
            r = subprocess.run(["sh", SCRIPT] + args, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, args)
            self.assertTrue(r.stderr.strip(), args)

    def test_fewer_than_keep(self):
        d = tempfile.mkdtemp()
        mk(d, ["a.tar"])
        r = subprocess.run(["sh", SCRIPT, d, "5"], capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout, os.listdir(d)), (0, "", ["a.tar"]))
