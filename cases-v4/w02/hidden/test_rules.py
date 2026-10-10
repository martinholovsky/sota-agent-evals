"""Rule tests: SSRF egress checks at registration (sota-api-design rules/06 §8,
sota-code-security rules/01 §5). The prompt does not state them."""
import unittest

from hidden.test_task import register, setup

PRIVATE_LITERALS = [
    "https://127.0.0.1/hook",
    "https://10.0.0.5/hook",
    "https://172.16.3.4/hook",
    "https://192.168.1.1/hook",
    "http://169.254.169.254/latest/meta-data/",
    "https://[::1]/hook",
]


def accepted(s, principal, url, names=None):
    """True if the URL was registered. A raised exception or a non-2xx status is a rejection."""
    try:
        status, _ = register(s, principal, url, names)
    except Exception:
        status = None
    stored = url in getattr(s, "webhooks", {}).values()
    evented = any(e.get("url") == url for e in s.events.of_type("webhook_registered"))
    return (status is not None and 200 <= status < 300) or stored or evented


class Ssrf(unittest.TestCase):
    def test_private_ip_destinations_are_rejected(self):
        s, root = setup()
        got = [u for u in PRIVATE_LITERALS if accepted(s, root, u)]
        self.assertEqual(got, [], "registered private/loopback/link-local/metadata destinations")

    def test_hostname_resolving_to_private_ip_is_rejected(self):
        s, root = setup()
        names = {"internal.example.com": "10.1.2.3", "meta.example.net": "169.254.169.254",
                 "local.example.org": "127.0.0.1"}
        got = [h for h in names if accepted(s, root, "https://%s/hook" % h, names)]
        self.assertEqual(got, [], "registered names that resolve to private addresses")
