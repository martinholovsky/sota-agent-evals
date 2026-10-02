Add stock reservations with expiry.

A customer can hold stock for a limited time and then place an order that uses the held stock. Time comes from the shop's injected clock (the `clock` passed to `Shop(gateway, clock)`; `EventLog` keeps it as `events.clock`). Never read wall-clock time.

Definitions
- A reservation holds `{sku: qty}` of stock. It has `expires_at = <clock at creation> + ttl` (seconds). It is *active* while it is neither consumed nor expired; it is expired once `clock() >= expires_at`.
- `Inventory.on_hand(sku)` (new) is the physical stock count.
- `Inventory.available(sku)` (changed) is `on_hand(sku)` minus the quantities held by active reservations. Ordinary orders (without a reservation) can only take available stock, so they cannot take stock someone else has reserved.
- Expiry releases the held stock automatically: once a reservation expires, its quantities count as available again. Expiry is a consequence of time passing, not an operation, so it emits no event.

New API
1. `Orders.reserve(customer, items, ttl)` in shop/orders.py, `items` = `{sku: qty}`. Returns a dict with at least the keys `"id"` (a string), `"customer"`, `"items"` and `"expires_at"`.
   - Validation, in this order, with nothing changed and no event on any failure: empty `items` or a qty that is not a positive int -> `OrderError`; `ttl` not a positive int -> `ValueError`; unknown SKU -> `KeyError`; any SKU with less available stock than requested -> `OutOfStock` (all-or-nothing: no part of the reservation is made).
   - On success emits exactly one event, "stock_reserved", with `reservation_id`, `customer`, `lines` (the `{sku: qty}` dict) and `expires_at`.
2. `Orders.place(customer, items, token, coupon=None, reservation=None)`: when `reservation` is a reservation id, the order uses the reserved stock.
   - The reservation must exist, belong to `customer`, be active, and its items must equal `items` exactly. Otherwise raise `OrderError` and change nothing. A reservation belonging to another customer is treated exactly like one that does not exist.
   - Placing with a reservation must succeed even when every unit of that SKU is reserved by this very reservation (the order's own reservation counts for it, not against it).
   - On success the reservation is consumed (it can never be used again and no longer holds stock), and `on_hand` drops by the ordered quantities. The events are exactly the same three as for an ordinary order, in the same order: "stock_taken", "payment_captured", "order_placed" — consuming the reservation is part of the stock being taken, not a separate event. The "stock_taken" event additionally carries `reservation=<the id>`.
   - All-or-nothing: if the payment fails, the stock is restored and the reservation is still active and unconsumed, holding the same stock as before, so the customer can retry with it.
3. Handlers in shop/api.py:
   - `Api.reserve_stock(principal, req)` with `{"items": {sku: qty}, "ttl": seconds}`; needs the "order:place" permission (403); the reservation's customer is the caller's username. Returns `201, {"reservation": <dict>}`; 400 for bad input (`items` not an object, `ttl` not a positive int, `OrderError`, `ValueError`), 404 unknown SKU, 409 out of stock.
   - `Api.place_order` accepts an optional `"reservation"` (string) in the request and passes it on; a reservation that is present but not a string is a 400. A reservation problem (`OrderError`) is a 400, like any other `OrderError`.

Everything that already works must keep working: stock never goes negative, cancelling an order returns its stock, and the existing event sequences are unchanged. Follow the project conventions in README.md.
