# Partial refunds

Support needs to refund part of an order (one broken mug out of three) without cancelling it.

Add `Api.refund_order(principal, {"id": str, "amount": int})`, where `amount` is in cents:

- Needs a new permission, `order:refund`, granted to admins only. Without it: 403.
- `amount` missing, not an int, or not positive: 400.
- Unknown order id: 404.
- Only orders in status `"paid"` can be refunded; any other status: 409.
- The total refunded on an order can never exceed what was charged (`quote["total"]`). A
  refund larger than what is left to refund: 409, and nothing changes.
- On success the amount is refunded through the payment gateway (`Payments.refund`), added to
  the order's `refunded` field, and the handler returns `(200, {"order": <updated order>})`.
  When the order has been refunded in full, its status becomes `"refunded"`. Several partial
  refunds on one order are fine.
- Events: the payment refund emits its usual `payment_refunded`; the order change emits
  `order_refunded` with `order_id` and `amount`.

`sales_summary` already nets out `refunded`, so reports pick partial refunds up with no change.
