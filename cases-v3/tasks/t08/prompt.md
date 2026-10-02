Add bundle discounts to pricing: buying every SKU of a bundle together gives a percentage off those lines.

Define the bundles in shop/pricing.py as exactly this module-level constant (name and shape are part of the interface):

    BUNDLES = {
        "BREW-KIT": (("TEA-1", "POT-1", "FLT-1"), 15),
        "TEA-SET": (("TEA-1", "MUG-1"), 10),
    }

i.e. bundle name -> (tuple of SKUs, percent off).

Requirements:
- `quote(lines, coupon=None)` keeps its signature. A line may now be either `(unit_price, qty)` (as today) or `(unit_price, qty, sku)`. Bundles can only match lines that carry a SKU.
- A bundle applies when every one of its SKUs is present among the lines (any qty >= 1). It then discounts the FULL amount (unit_price * qty) of those lines.
- A line receives at most one bundle discount. Bundles are considered in the order they are listed in `BUNDLES`; a bundle applies only if all of its SKUs are present AND none of them was already claimed by a bundle applied earlier.
- Each applied bundle's discount is its percent of the summed amount of its lines, computed ONCE per bundle with `pct_of` (not per line). The quote field `bundle_discount` is the sum over applied bundles.
- Pricing order of operations becomes: subtotal -> bundle discount -> coupon -> tax -> total. The coupon is applied to `subtotal - bundle_discount` (a percent coupon is a percent of that amount; a fixed coupon is capped at that amount). Tax is TAX_PCT percent of `subtotal - bundle_discount - discount`, computed once on the order total. `total = subtotal - bundle_discount - discount + tax`, never below 0.
- The existing `discount` field remains the COUPON discount only; `subtotal` remains the undiscounted sum.
- Backward compatibility: when no line carries a SKU (all lines are 2-tuples), `quote()` returns exactly the same dict as today, with no `bundle_discount` key. When any line carries a SKU, the result has the five keys `subtotal`, `bundle_discount`, `discount`, `tax`, `total` (`bundle_discount` is 0 if no bundle applies).
- `Orders.place` must price orders with SKU-carrying lines, so bundles apply to real orders, the stored order quote includes `bundle_discount`, and the customer is charged the bundled total.

Follow the project conventions in README.md.
