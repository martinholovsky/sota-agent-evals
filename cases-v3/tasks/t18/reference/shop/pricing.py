"""Order pricing. Order of operations is fixed and documented:

1. subtotal  = sum(unit_price * qty) over lines
2. discount  = coupon discount on the subtotal (at most one coupon)
3. tax       = TAX_PCT percent of (subtotal - discount), round half up, computed ONCE
               on the order total (never per line)
4. total     = subtotal - discount + tax, never below 0
"""
from .money import pct_of

TAX_PCT = 20

# Built-in coupons, code -> ("pct", n) | ("fixed", cents). Each shop's coupon registry
# (shop/coupons.py) starts with these; quote() uses them when no registry is given.
COUPONS = {
    "TEN": ("pct", 10),
    "FIVEOFF": ("fixed", 500),
}


def quote(lines: list, coupon: str | None = None, *, coupons=None) -> dict:
    """lines: [(unit_price_cents, qty)]. Returns subtotal/discount/tax/total in cents.
    coupons: a shop.coupons.Coupons registry to resolve `coupon` in (default: built-ins)."""
    subtotal = sum(price * qty for price, qty in lines)
    discount = 0
    if coupon is not None:
        if coupons is not None:
            kind, val = coupons.rule(coupon)
        elif coupon not in COUPONS:
            raise ValueError("unknown coupon: %r" % coupon)
        else:
            kind, val = COUPONS[coupon]
        discount = pct_of(subtotal, val) if kind == "pct" else min(val, subtotal)
    taxable = subtotal - discount
    tax = pct_of(taxable, TAX_PCT)
    return {"subtotal": subtotal, "discount": discount, "tax": tax,
            "total": max(0, taxable + tax)}
