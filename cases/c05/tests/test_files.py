import os
import tempfile
import unittest
from src.files import read_report


class T(unittest.TestCase):
    def test_reads(self):
        d = tempfile.mkdtemp()
        open(os.path.join(d, "q1.txt"), "w").write("ok")
        self.assertEqual(read_report(d, "q1.txt"), "ok")
