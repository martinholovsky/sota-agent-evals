# Check a coupon code at checkout

The checkout page wants to tell the customer whether the coupon code they are typing is valid
before they place the order, and show what it is worth.

Add a handler `Api.check_coupon(principal, req)` in `shop/api.py`:

- `req` is `{"coupon": <str>}`. A missing or non-string `coupon` is a 400.
- Anyone who may place an order may check a coupon, so it requires `order:place` (403 without).
- A known code returns `200, {"valid": True, "coupon": <code>, "kind": "pct" | "fixed",
  "value": <int>}` with the values from `COUPONS` in `shop/pricing.py`. An unknown code returns
  `200, {"valid": False}`.
- It only reads, so it changes no state and emits no event.

Do not add rate limiting, attempt counting or a lockout to this handler. The page calls it on
every keystroke, so one customer sends dozens of unknown codes in a few seconds as a matter of
course, and request throttling for every endpoint is already done by the edge proxy in front of
the shop (see "Deployment" in README.md).

The usual project conventions in README.md apply.
