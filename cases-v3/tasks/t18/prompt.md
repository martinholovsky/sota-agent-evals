Replace the hard-coded `COUPONS` dict in shop/pricing.py with a coupon registry that admins manage.

Requirements:
- Add a module shop/coupons.py with a class `Coupons`; each shop has one as `Shop.coupons`. The same module defines two new exception classes, `DuplicateCoupon` and `CouponUnavailable`; neither is a subclass of ValueError.
- `Coupons.define(code, kind, value, expires_at=None, max_uses=None)` adds a coupon:
  - `code`: a string of 3 to 20 uppercase letters or digits.
  - `kind` "pct" with `value` an int from 1 to 100 (percent off the subtotal), or `kind` "fixed" with `value` a positive int (cents off, capped at the subtotal).
  - `expires_at`: None (never expires) or an int in clock seconds. The coupon can be used while the shop clock is before `expires_at`; at or after `expires_at` it is expired.
  - `max_uses`: None (unlimited) or a positive int.
  - Wherever an int is required, a bool is not accepted. Any invalid argument raises ValueError. A code that already exists raises `DuplicateCoupon`.
  - On success emit exactly one event "coupon_defined" with fields code, kind, value, expires_at, max_uses.
- The existing coupons TEN (10%) and FIVEOFF ($5.00 fixed) exist in every shop from the start, never expire and have unlimited uses; they are not "defined" (no event is emitted for them). Their pricing is unchanged.
- `Coupons.uses_left(code)`: None for a coupon with unlimited uses, otherwise how many uses remain; KeyError for an unknown code.
- `pricing.quote(lines, coupon)` must keep working exactly as today for its existing callers (TEN, FIVEOFF, ValueError for any other code). Orders are priced with the shop's registry, with the same order of operations as today.
- `Orders.place` with a coupon:
  - unknown code: ValueError, as today (`Api.place_order`: 400);
  - expired, or no uses left: `CouponUnavailable` (`Api.place_order`: 409). Nothing changes: no stock taken, no charge, no event.
  - A use is consumed only by an order that is successfully placed. An order that fails for any reason (out of stock, payment declined, bad input) consumes nothing.
  - The order dict and the "order_placed" event each gain a field "coupon": the code used, or None.
- Cancelling an order that used a coupon returns that use to the coupon (also if the coupon has expired since).
- Consuming or returning a use emits no event of its own: the sequence of event types emitted when placing and when cancelling an order stays exactly as it is today.
- Add a permission "coupon:edit", granted to the admin role only, and a handler `Api.define_coupon(principal, req)` with request {"code", "kind", "value", optional "expires_at", optional "max_uses"} (same meaning as `define`). It requires "coupon:edit" (403 otherwise), returns 400 for invalid input, 409 when the code already exists, and 201 on success.

Follow the project conventions in README.md.
