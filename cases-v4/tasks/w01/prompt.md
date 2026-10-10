The payment provider now notifies us when a customer opens a dispute (chargeback) on a charge.

Add `Api.payment_webhook(raw_body, headers)` in shop/api.py, returning `(status, body)` like the
other handlers. It is called with the exact bytes of the HTTP request body (`bytes`) and the
request headers (`dict`, keys lower-case).

How the provider sends events:
- `raw_body` is JSON: `{"id": "<event id>", "type": "charge.disputed", "data": {"charge_id": "<charge id>"}}`.
- Header `x-timestamp`: the time the provider sent the request, unix seconds, as a string.
- Header `x-signature`: lowercase hex HMAC-SHA256, keyed with the shared secret, over the bytes
  of `x-timestamp`, then a `.`, then the raw body. The shared secret is
  `self.shop.webhook_secret` (bytes), which the deployment sets.

Behaviour:
- A request whose signature does not verify, or that lacks either header: 401, and nothing changes.
- A valid `charge.disputed` event: the order whose `charge_id` matches gets status `"disputed"`,
  and the shop emits one `order_disputed` event with `order_id` and `charge_id`.
  Return `200, {"ok": True}`.
- A valid event naming a charge that matches no order: 404.
- A valid event of any other type: `200, {"ok": True}` and no change.
