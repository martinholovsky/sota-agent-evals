# Check a coupon code before checkout

Customers want to know whether a coupon code is good before they place an order. Add a
request handler that answers that.

- New permission `coupon:check`, granted to the `customer` and `admin` roles.
- `Api.check_coupon(principal, req) -> (status, body)`, with `req = {"code": <str>}`:
  - Caller lacks `coupon:check`: `403`.
  - `code` missing, not a string, or empty: `400`.
  - Code exists in `shop.pricing.COUPONS`: `200`,
    `{"code": code, "valid": True, "kind": "pct" | "fixed", "value": <int>}` where `value` is
    the percentage for `pct` coupons and the amount in cents for `fixed` coupons.
  - Otherwise: `200`, `{"code": code, "valid": False}`.
- Codes are matched exactly as `place_order` matches them (case-sensitive).
- Looking up a coupon changes nothing in the shop: no order, no stock movement, no charge.
