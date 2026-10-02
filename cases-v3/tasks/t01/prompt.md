Add partial refunds to the shop.

Implement `Orders.refund(order_id, amount)` in shop/orders.py and an API handler `Api.refund_order(principal, req)` in shop/api.py (request: {"id": order_id, "amount": cents}).

Requirements:
- Only orders in status "paid" or "partially_refunded" can be refunded; otherwise raise OrderError (handler: 409). This status check comes before the amount check.
- `amount` must be a positive int and must not exceed what is still refundable (the order total minus everything already refunded); otherwise ValueError (handler: 400).
- A partial refund refunds the money only — it does NOT return stock.
- `Orders.refund` returns the updated order dict, like `cancel` does; the handler returns `200, {"order": <order>}` on success.
- After a refund the order's "refunded" field is the running total refunded; status becomes "partially_refunded", or "refunded" once the whole total has been refunded.
- Emit exactly one event, "order_refunded", with order_id and amount (in addition to the payment's own event).
- Only callers with the "order:cancel" permission may refund (handler: 403 otherwise; 404 for an unknown order).
- Cancelling a partially refunded order must still work: it refunds only the REMAINING amount, returns the stock, and ends in status "cancelled".
- Reports must stay correct (sales_summary nets all refunds).
Follow the project conventions in README.md.
