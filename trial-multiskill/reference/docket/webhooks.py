"""Outbound webhook destination checks and the default network callables."""
import ipaddress
import socket
import ssl
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})
MAX_URL_LENGTH = 2048
HTTP_TIMEOUT_SECONDS = 10


def destination_problem(url, resolve):
    """None if `url` is an acceptable webhook target, else a short reason.

    Called both when the URL is saved and again before every delivery, because
    what a name resolves to can change between the two (DNS rebinding)."""
    if not isinstance(url, str) or not url or len(url) > MAX_URL_LENGTH:
        return "invalid URL"
    try:
        parts = urlsplit(url)
        port = parts.port  # raises ValueError on a malformed port
    except ValueError:
        return "invalid URL"
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        return "scheme not allowed"
    if parts.username is not None or parts.password is not None:
        return "credentials in URL not allowed"
    host = parts.hostname
    if not host:
        return "missing host"
    if port == 0:
        return "invalid port"
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            raw = resolve(host)
        except Exception:
            return "host does not resolve"
        try:
            addresses = [ipaddress.ip_address(str(a).split("%", 1)[0]) for a in raw]
        except ValueError:
            return "host does not resolve"
    if not addresses:
        return "host does not resolve"
    for addr in addresses:
        if addr.version == 6 and addr.ipv4_mapped is not None:
            addr = addr.ipv4_mapped
        if not addr.is_global or addr.is_multicast:
            return "destination address not allowed"
    return None


def default_resolve(host):
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return sorted({info[4][0] for info in infos})


def _opener():
    # Only HTTP(S); no redirect handler, so a 3xx is returned as a failure
    # instead of being followed to a destination nobody validated.
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.HTTPHandler(),
                    urllib.request.HTTPSHandler(context=ssl.create_default_context()),
                    urllib.request.HTTPDefaultErrorHandler(),
                    urllib.request.HTTPErrorProcessor()):
        opener.add_handler(handler)
    return opener


def default_http_post(url, body, headers):
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with _opener().open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            response.read(65536)
            return response.status
    except urllib.error.HTTPError as err:
        return err.code
