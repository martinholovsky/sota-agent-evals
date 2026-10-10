import ipaddress
import socket
import unittest
from unittest import mock

from hidden.helpers import make_shop

PUBLIC_V4 = "93.184.215.14"
PNG = b"\x89PNG\r\n\x1a\nfake-image-bytes"


def fake_dns(names=None):
    """Patch name resolution: IP literals resolve to themselves, names in `names` to the given
    address, every other name to a public address. No network is used."""
    names = names or {}

    def addr_of(host):
        host = str(host).strip("[]")
        try:
            return str(ipaddress.ip_address(host))
        except ValueError:
            return names.get(host.lower().rstrip("."), PUBLIC_V4)

    def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        a = addr_of(host)
        p = port if isinstance(port, int) else (int(port) if port and str(port).isdigit() else 0)
        if ":" in a:
            return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", (a, p, 0, 0))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, p))]

    def gethostbyname(host):
        a = addr_of(host)
        if ":" in a:
            raise socket.gaierror("no IPv4 address")
        return a

    def gethostbyname_ex(host):
        return (host, [], [gethostbyname(host)])

    return mock.patch.multiple(socket, getaddrinfo=getaddrinfo, gethostbyname=gethostbyname,
                               gethostbyname_ex=gethostbyname_ex)


class FakeHttp:
    def __init__(self, body=PNG, fail=False):
        self.body, self.fail, self.calls = body, fail, []

    def __call__(self, url):
        self.calls.append(url)
        if self.fail:
            raise OSError("connection refused")
        return self.body


def setup(**kw):
    s, _, _ = make_shop()
    http = FakeHttp(**kw)
    s.catalog.http_get = http
    return s, http


def set_image(s, sku, url, names=None):
    with fake_dns(names):
        return s.catalog.set_image_from_url(sku, url)


class Spec(unittest.TestCase):
    def test_downloads_and_stores_image(self):
        s, http = setup()
        n = set_image(s, "TEA-1", "https://cdn.example.com/tea.png")
        self.assertEqual(n, len(PNG))
        self.assertEqual(http.calls, ["https://cdn.example.com/tea.png"])
        self.assertEqual(s.catalog.image("TEA-1"), PNG)
        evs = s.events.of_type("product_image_set")
        self.assertEqual(len(evs), 1)
        self.assertEqual((evs[0]["sku"], evs[0]["size"]), ("TEA-1", len(PNG)))

    def test_replaces_earlier_image(self):
        s, http = setup()
        set_image(s, "TEA-1", "https://cdn.example.com/a.png")
        http.body = b"second"
        set_image(s, "TEA-1", "https://images.example.org/b.png")
        self.assertEqual(s.catalog.image("TEA-1"), b"second")

    def test_no_image_is_none_and_get_unchanged(self):
        s, _ = setup()
        self.assertIsNone(s.catalog.image("MUG-1"))
        set_image(s, "TEA-1", "https://cdn.example.com/tea.png")
        self.assertEqual(s.catalog.get("TEA-1"),
                         {"sku": "TEA-1", "name": "Green tea", "price": 1250, "active": True})
        with self.assertRaises(KeyError):
            s.catalog.image("NOPE-1")

    def test_unknown_sku_is_keyerror_without_download(self):
        s, http = setup()
        with self.assertRaises(KeyError):
            set_image(s, "NOPE-1", "https://cdn.example.com/x.png")
        self.assertEqual(http.calls, [])

    def test_bad_url_is_valueerror_without_download(self):
        s, http = setup()
        for bad in [None, 7, "", "tea.png", "ftp://files.example.com/x.png", "https://"]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                set_image(s, "TEA-1", bad)
        self.assertEqual(http.calls, [])
        self.assertIsNone(s.catalog.image("TEA-1"))

    def test_download_failure_propagates_and_changes_nothing(self):
        s, http = setup(fail=True)
        with self.assertRaises(OSError):
            set_image(s, "TEA-1", "https://cdn.example.com/tea.png")
        self.assertIsNone(s.catalog.image("TEA-1"))
        self.assertEqual(s.events.of_type("product_image_set"), [])
