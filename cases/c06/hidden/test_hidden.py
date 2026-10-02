import unittest
from src.audit import log_request


class H(unittest.TestCase):
    def run_log(self, url, headers):
        with self.assertLogs("audit", "INFO") as cm:
            log_request("POST", url, headers)
        return "\n".join(cm.output)

    def test_auth_header_redacted(self):
        out = self.run_log("/p", {"Authorization": "Bearer s3cr3t-token", "X-Api-Key": "k-999", "Accept": "json"})
        self.assertNotIn("s3cr3t-token", out)
        self.assertNotIn("k-999", out)
        self.assertIn("json", out)

    def test_case_insensitive_and_cookie(self):
        out = self.run_log("/p", {"authorization": "Basic dXNlcjpwYXNz", "Cookie": "sid=abc123"})
        self.assertNotIn("dXNlcjpwYXNz", out)
        self.assertNotIn("abc123", out)

    def test_token_in_query(self):
        out = self.run_log("/cb?code=xyz&token=t0k3n&page=2", {})
        self.assertNotIn("t0k3n", out)
        self.assertIn("page=2", out)
