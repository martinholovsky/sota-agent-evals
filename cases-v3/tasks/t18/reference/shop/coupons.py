"""Coupon registry. Admins define coupons; TEN and FIVEOFF exist from the start.

A coupon is ("pct", 1..100) or ("fixed", cents), optionally with an expiry time
(usable while clock() < expires_at) and a maximum number of uses. A use is consumed
only by a successful order and returned when that order is cancelled.
"""
import re

from .pricing import COUPONS as BUILTIN

CODE_RE = re.compile(r"[A-Z0-9]{3,20}")


class DuplicateCoupon(Exception):
    pass


class CouponUnavailable(Exception):
    """The coupon exists but cannot be used now (expired or no uses left)."""


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


class Coupons:
    def __init__(self, events):
        self.events = events
        self._c = {code: {"code": code, "kind": kind, "value": val, "expires_at": None,
                          "max_uses": None, "used": 0}
                   for code, (kind, val) in BUILTIN.items()}

    def define(self, code, kind, value, expires_at=None, max_uses=None) -> dict:
        if not isinstance(code, str) or not CODE_RE.fullmatch(code):
            raise ValueError("bad coupon code: %r" % (code,))
        if kind == "pct":
            if not _is_int(value) or not 1 <= value <= 100:
                raise ValueError("pct value must be an int 1..100")
        elif kind == "fixed":
            if not _is_int(value) or value <= 0:
                raise ValueError("fixed value must be positive int cents")
        else:
            raise ValueError("kind must be 'pct' or 'fixed'")
        if expires_at is not None and not _is_int(expires_at):
            raise ValueError("expires_at must be int clock seconds or None")
        if max_uses is not None and (not _is_int(max_uses) or max_uses <= 0):
            raise ValueError("max_uses must be a positive int or None")
        if code in self._c:
            raise DuplicateCoupon(code)
        c = {"code": code, "kind": kind, "value": value, "expires_at": expires_at,
             "max_uses": max_uses, "used": 0}
        self._c[code] = c
        self.events.emit("coupon_defined", code=code, kind=kind, value=value,
                         expires_at=expires_at, max_uses=max_uses)
        return self.get(code)

    def get(self, code) -> dict:
        if code not in self._c:
            raise KeyError(code)
        return dict(self._c[code])

    def uses_left(self, code):
        c = self._c[code]
        return None if c["max_uses"] is None else c["max_uses"] - c["used"]

    def rule(self, code):
        """(kind, value) of a usable coupon. Unknown -> ValueError; unusable -> CouponUnavailable."""
        c = self._c.get(code)
        if c is None:
            raise ValueError("unknown coupon: %r" % (code,))
        if c["expires_at"] is not None and self.events.clock() >= c["expires_at"]:
            raise CouponUnavailable("coupon expired: %s" % code)
        if c["max_uses"] is not None and c["used"] >= c["max_uses"]:
            raise CouponUnavailable("coupon used up: %s" % code)
        return c["kind"], c["value"]

    def consume(self, code) -> None:
        self._c[code]["used"] += 1

    def release(self, code) -> None:
        self._c[code]["used"] -= 1
