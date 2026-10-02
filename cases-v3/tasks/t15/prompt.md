Add idempotency keys to order placement, so a client that retries a request (for example after a timeout) can never be charged twice.

`Orders.place(customer, items, token, coupon=None, idempotency_key=None)` in shop/orders.py:
- With `idempotency_key=None` nothing changes.
- Keys are scoped per customer: the same key string used by two different customers refers to two unrelated requests.
- The first SUCCESSFUL `place` for a (customer, key) pair records the key against the order it created.
- A later call with the same customer and key and the **same request** returns that original order — as `Orders.get` returns it now (so, e.g., with its current status if it was cancelled since) — and does nothing else: no stock taken, no charge, no new order, no event. "Same request" means equal `items` (compared as a mapping: key order does not matter) and equal `coupon`. The `token` is NOT part of the comparison (a retry may carry a fresh payment token).
- The same customer and key with a **different request** raises `IdempotencyConflict`, a new exception class in shop/orders.py that is a subclass of `OrderError`; nothing changes and no event is emitted.
- A call that fails (bad quantity, unknown SKU, unknown coupon, out of stock, declined payment, ...) does NOT consume the key: a later call with that key is handled as if the key had never been used — including a call with a different request.
- Recording a key is part of placing the order and emits no event of its own: a successful first placement emits exactly the same events as today.

`Api.place_order` in shop/api.py:
- Accepts an optional `"idempotency_key"` in the request. If present it must be a non-empty string, else 400 (before anything else happens).
- A replay returns 201 `{"order": <the original order, as above>}` — the same status as the original success.
- `IdempotencyConflict` is 409 with `{"error": ...}`.
- A declined payment (GatewayError from the gateway) now returns 402 `{"error": ...}` instead of propagating as an exception.
- Every other outcome stays exactly as it is today.

Follow the project conventions in README.md.
