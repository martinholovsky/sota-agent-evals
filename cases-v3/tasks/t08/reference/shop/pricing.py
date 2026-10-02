"""Order pricing. Order of operations is fixed and documented:

1. subtotal        = sum(unit_price * qty) over lines
2. bundle_discount = for each applied bundle, its percent of the summed amount of its lines
                     (lines must carry a SKU; a line gets at most one bundle; bundles are
                     considered in BUNDLES order)
3. discount        = coupon discount on (subtotal - bundle_discount) (at most one coupon)
4. tax             = TAX_PCT percent of (subtotal - bundle_discount - discount), round half up,
                     computed ONCE on the order total (never per line)
5. total           = subtotal - bundle_discount - discount + tax, never below 0

Lines are (unit_price, qty) or (unit_price, qty, sku). With no SKU-carrying line the result
has no "bundle_discount" key (the pre-bundle shape).
"""
from .money import pct_of

TAX_PCT = 20

# code -> ("pct", n) | ("fixed", cents)
COUPONS = {
    "TEN": ("pct", 10),
    "FIVEOFF": ("fixed", 500),
}

# name -> (skus, percent off those lines)
BUNDLES = {
    "BREW-KIT": (("TEA-1", "POT-1", "FLT-1"), 15),
    "TEA-SET": (("TEA-1", "MUG-1"), 10),
}


def _bundle_discount(lines: list) -> int:
    amount = {}
    for line in lines:
        if len(line) == 3:
            price, qty, sku = line
            amount[sku] = amount.get(sku, 0) + price * qty
    claimed, total = set(), 0
    for skus, pct in BUNDLES.values():
        if all(s in amount and s not in claimed for s in skus):
            claimed.update(skus)
            total += pct_of(sum(amount[s] for s in skus), pct)
    return total


def quote(lines: list, coupon: str | None = None) -> dict:
    """lines: [(unit_price_cents, qty[, sku])]. Returns the priced quote in cents."""
    subtotal = sum(line[0] * line[1] for line in lines)
    with_skus = any(len(line) == 3 for line in lines)
    bundle = _bundle_discount(lines) if with_skus else 0
    base = subtotal - bundle
    discount = 0
    if coupon is not None:
        if coupon not in COUPONS:
            raise ValueError("unknown coupon: %r" % coupon)
        kind, val = COUPONS[coupon]
        discount = pct_of(base, val) if kind == "pct" else min(val, base)
    taxable = base - discount
    tax = pct_of(taxable, TAX_PCT)
    q = {"subtotal": subtotal, "discount": discount, "tax": tax, "total": max(0, taxable + tax)}
    if with_skus:
        q["bundle_discount"] = bundle
    return q
