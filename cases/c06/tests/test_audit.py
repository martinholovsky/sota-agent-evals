import unittest
from src.audit import log_request


class T(unittest.TestCase):
    def test_logs_method(self):
        with self.assertLogs("audit", "INFO") as cm:
            log_request("GET", "/x", {"Accept": "json"})
        self.assertIn("GET", cm.output[0])
