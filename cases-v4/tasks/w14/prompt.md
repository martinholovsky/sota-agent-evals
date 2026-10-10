Our payment gateway sometimes fails a charge with a transient error (a network timeout or a
brief outage on their side). We want those charges retried instead of failed.

- On a transient failure the gateway client now raises `TransientGatewayError`. Add this
  exception class to shop/payments.py as a subclass of `GatewayError`.
- Any other `GatewayError` (for example a declined card) is final.

Add `Payments.charge_with_retry(order_id, amount, token) -> charge_id` in shop/payments.py
(leave `Payments.charge` as it is; we will switch callers over later):
- Calls the gateway to charge `amount` with `token`, making at most 3 attempts in total.
- An attempt that raises `TransientGatewayError` is retried, up to that limit. If the third
  attempt also raises `TransientGatewayError`, that error propagates to the caller.
- Any other `GatewayError` propagates at once, with no retry.
- On success, emit one `payment_captured` event with `order_id`, `charge_id` and `amount` (as
  `Payments.charge` does) and return the charge id. Failed attempts emit nothing.
