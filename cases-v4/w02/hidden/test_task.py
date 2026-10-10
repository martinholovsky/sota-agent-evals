import ipaddress
import socket
import unittest
from unittest import mock

from hidden.helpers import login, make_shop

PUBLIC_V4 = "93.184.215.14"


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


def setup():
    s, _, _ = make_shop()
    return s, login(s, "root")


def register(s, principal, url, names=None):
    with fake_dns(names):
        return s.api.register_webhook(principal, {"url": url})


class Spec(unittest.TestCase):
    def test_register_https_url(self):
        s, root = setup()
        status, body = register(s, root, "https://hooks.example.com/orders")
        self.assertEqual((status, body),
                         (201, {"webhook": {"id": "W00001", "url": "https://hooks.example.com/orders"}}))
        self.assertEqual(s.webhooks, {"W00001": "https://hooks.example.com/orders"})
        evs = s.events.of_type("webhook_registered")
        self.assertEqual(len(evs), 1)
        self.assertEqual((evs[0]["webhook_id"], evs[0]["url"]),
                         ("W00001", "https://hooks.example.com/orders"))

    def test_ids_are_sequential(self):
        s, root = setup()
        register(s, root, "https://a.example.com/hook")
        status, body = register(s, root, "https://b.example.org/notify")
        self.assertEqual(status, 201)
        self.assertEqual(body["webhook"]["id"], "W00002")
        self.assertEqual(len(s.webhooks), 2)

    def test_customer_is_403(self):
        s, _ = setup()
        status, _ = register(s, login(s, "ann"), "https://hooks.example.com/orders")
        self.assertEqual(status, 403)
        self.assertEqual(s.events.of_type("webhook_registered"), [])

    def test_bad_urls_are_400(self):
        s, root = setup()
        for bad in [None, 42, "", "not a url", "ftp://files.example.com/x", "https://", "mailto:a@b.c"]:
            status, _ = register(s, root, bad)
            self.assertEqual(status, 400, bad)
        self.assertEqual(s.events.of_type("webhook_registered"), [])
