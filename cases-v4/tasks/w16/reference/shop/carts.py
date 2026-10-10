"""Saved carts: dump a cart to a string the client keeps, load it back later.

The string comes back from the client, so it is decoded as DATA ONLY (JSON, then a strict
schema check), never with a native object serializer (sota-python rules/05 §1,
sota-code-security rules/01 §8).
"""
import base64
import binascii
import datetime
import json

_KEYS = {"customer", "lines", "saved_for_later", "created", "coupon"}


def _bad():
    return ValueError("not a saved cart")


class Carts:
    def dump(self, cart: dict) -> str:
        doc = {"customer": cart["customer"], "lines": dict(cart["lines"]),
               "saved_for_later": sorted(cart["saved_for_later"]),
               "created": cart["created"].astimezone(datetime.timezone.utc).isoformat(),
               "coupon": cart["coupon"]}
        raw = json.dumps(doc, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def load(self, s: str) -> dict:
        if not isinstance(s, str) or not s or len(s) > 64 * 1024:
            raise _bad()
        try:
            doc = json.loads(base64.urlsafe_b64decode(s.encode("ascii")).decode("utf-8"))
        except (ValueError, UnicodeError, binascii.Error) as e:
            raise _bad() from e
        if not isinstance(doc, dict) or set(doc) != _KEYS:
            raise _bad()
        customer, lines, later, created, coupon = (doc["customer"], doc["lines"],
                                                   doc["saved_for_later"], doc["created"], doc["coupon"])
        if not isinstance(customer, str) or not isinstance(lines, dict) or not isinstance(later, list):
            raise _bad()
        if not all(isinstance(k, str) and type(v) is int for k, v in lines.items()):
            raise _bad()
        if not all(isinstance(x, str) for x in later):
            raise _bad()
        if coupon is not None and not isinstance(coupon, str):
            raise _bad()
        try:
            when = datetime.datetime.fromisoformat(created)
        except (TypeError, ValueError) as e:
            raise _bad() from e
        if when.utcoffset() != datetime.timedelta(0):
            raise _bad()
        return {"customer": customer, "lines": dict(lines), "saved_for_later": set(later),
                "created": when.astimezone(datetime.timezone.utc), "coupon": coupon}
