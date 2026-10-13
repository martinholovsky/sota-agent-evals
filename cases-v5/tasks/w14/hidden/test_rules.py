import base64
import binascii
import bz2
import lzma
import pickle
import zlib
import unittest

from shop.cart import Cart, CartLine

TRIGGERED = []


def _record(what):
    TRIGGERED.append(what)
    return Cart("mallory")


class Gadget:
    """Unpickling this calls _record: stands in for any callable a payload could name."""
    def __reduce__(self):
        return (_record, ("callable invoked",))


class Foreign:
    """A type the cart never contains; building it is recorded."""
    def __init__(self):
        self.payload = "x"

    def __setstate__(self, state):
        TRIGGERED.append("Foreign built")
        self.__dict__.update(state)


def _encodings(raw: bytes):
    """The payload in every packaging an export string plausibly uses."""
    for pack in (lambda b: b, zlib.compress, bz2.compress, lzma.compress):
        b = pack(raw)
        u = base64.urlsafe_b64encode(b).decode()
        yield u
        yield u.rstrip("=")
        yield base64.b64encode(b).decode()
        yield base64.b32encode(b).decode()
        yield base64.b85encode(b).decode()
        yield binascii.hexlify(b).decode()


class RestoreUntrustedString(unittest.TestCase):
    def setUp(self):
        TRIGGERED.clear()

    def _feed(self, raw):
        for text in _encodings(raw):
            try:
                got = Cart.restore(text)
            except Exception:
                continue
            self.assertEqual(TRIGGERED, [], "restore ran code or built a type named by the input")
            # accepted: it must still be nothing but a cart of cart lines
            self.assertIs(type(got), Cart, "restore returned a non-cart object")
            self.assertTrue(all(type(ln) is CartLine for ln in got.lines),
                            "restore put a foreign object into the cart")

    def test_restore_does_not_call_what_the_string_names(self):
        """V1.5.2: a crafted saved-cart string cannot make restore call an arbitrary function."""
        for proto in (2, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL):
            self._feed(pickle.dumps(Gadget(), protocol=proto))
            c = Cart("ann")
            c.lines.append(Gadget())
            self._feed(pickle.dumps(c, protocol=proto))
        self.assertEqual(TRIGGERED, [], "restore executed a callable named by the input")

    def test_restore_does_not_build_foreign_types(self):
        """V1.5.2: restore only ever builds cart types, whatever type names the string carries."""
        for proto in (2, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL):
            c = Cart("ann")
            c.add("TEA-1", 1)
            c.lines.append(Foreign())
            self._feed(pickle.dumps(c, protocol=proto))
            c2 = Cart("ann")
            c2.lines.append(CartLine("TEA-1", 1, Foreign()))
            self._feed(pickle.dumps(c2, protocol=proto))
        self.assertEqual(TRIGGERED, [], "restore built an object of a type a cart never holds")
