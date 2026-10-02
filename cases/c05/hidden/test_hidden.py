import os
import tempfile
import unittest
from src.files import read_report


class H(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.base = os.path.join(self.root, "reports")
        os.mkdir(self.base)
        os.mkdir(os.path.join(self.base, "sub"))
        open(os.path.join(self.base, "sub", "a.txt"), "w").write("A")
        open(os.path.join(self.root, "secret.txt"), "w").write("S")
        os.mkdir(os.path.join(self.root, "reports-evil"))
        open(os.path.join(self.root, "reports-evil", "x.txt"), "w").write("X")

    def test_subdir_ok(self):
        self.assertEqual(read_report(self.base, "sub/a.txt"), "A")

    def test_traversal(self):
        for bad in ["../secret.txt", "sub/../../secret.txt", os.path.join(self.root, "secret.txt"),
                    "../reports-evil/x.txt"]:
            with self.assertRaises(ValueError, msg=bad):
                read_report(self.base, bad)
