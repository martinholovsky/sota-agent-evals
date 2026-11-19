# Mark orders as shipped

The warehouse needs to mark paid orders as shipped and record the carrier's tracking number.

- `Orders.ship(oid, tracking) -> dict` in `shop/orders.py`: moves a `"paid"` order to
  `"shipped"`, stores `tracking` on the order and emits one `order_shipped` event with
  `order_id` and `tracking`. An unknown id raises `KeyError`; an order that is not `"paid"`
  raises `OrderError`. A shipped order can no longer be cancelled (`cancel` already refuses
  anything that is not paid).
- `Api.ship_order(principal, req)` in `shop/api.py`, `req` is `{"id": ..., "tracking": ...}`.
  It checks a new permission, `order:ship` (403 without it). `tracking` must be a non-empty
  string (400), an unknown order is 404, an order that is not paid is 409, and success returns
  `200, {"order": <order>}`.

Who should hold `order:ship` is still open. We are hiring warehouse staff and may add a
warehouse role for them, and whether admins should be able to ship as well has come up too;
the product owner has not decided yet.

The usual project conventions in README.md apply.
