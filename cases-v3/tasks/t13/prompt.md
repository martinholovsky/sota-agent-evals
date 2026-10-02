Add per-customer purchase limits to the shop.

1. `Catalog.set_purchase_limit(sku, max_units)` in shop/catalog.py: `max_units` is a positive int (not a bool), or `None` to remove the limit. Unknown SKU: KeyError. Any other value: ValueError. Emits exactly one event, `"purchase_limit_set"`, with `sku` and `limit` (the new value, possibly None).

2. Enforcement in `Orders.place` (shop/orders.py). For every SKU in the order that has a limit, count the units of that SKU this customer bought in orders placed within the rolling last 24 hours, plus the units requested now; if that exceeds the limit, the order is rejected. Precisely:
   - "Now" is the shop clock (the `clock` passed to `Shop`). An earlier order counts only if it was placed less than 86 400 seconds before now (an order placed exactly 86 400 seconds ago no longer counts).
   - Cancelled orders do not count; every other order does.
   - Limits are per customer: other customers' orders never count.
   - Raise `PurchaseLimitExceeded`, a new exception class in shop/orders.py that is a subclass of `OrderError`.
   - Check limits after validating quantities and SKUs and BEFORE stock or payment: a rejected order changes nothing at all — no stock taken, no charge, no order, and no event of any kind. When both a limit and stock would fail, `PurchaseLimitExceeded` wins.
   - The order is all-or-nothing: if any line exceeds its limit, nothing is bought.

3. API (shop/api.py):
   - `Api.place_order` returns 409 with `{"error": ...}` when the order exceeds a purchase limit. Every other outcome of `place_order` stays exactly as it is today.
   - New handler `Api.set_purchase_limit(principal, req)`, request `{"sku": <str>, "limit": <positive int or null>}`; requires the existing `catalog:edit` permission (403 otherwise); unknown SKU 404; bad limit 400; success 200 `{"sku": sku, "limit": limit}`.

Follow the project conventions in README.md.
