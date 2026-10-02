Add a payment-gateway webhook receiver so the shop learns about card disputes.

Implement an API handler `Api.payment_webhook(req)` in shop/api.py. It takes ONLY the request (a webhook has no logged-in principal) and returns `(status_code, body_dict)` like every other handler. The request is:

    {"headers": {"Shop-Timestamp": "<unix seconds>", "Shop-Signature": "<hex>"},
     "body": "<the raw request body, a JSON string>"}

Configuration: the shared secret is the attribute `webhook_secret` on the shop's `Payments` object (`shop.payments.webhook_secret`, type `bytes`). It defaults to `None`. Do not change the signatures of `Shop(...)` or `Payments(...)`.

Requirements, checked in this order:
1. `headers` must be a dict containing both `Shop-Timestamp` and `Shop-Signature` as strings, the timestamp must consist only of decimal digits, and `body` must be a string; otherwise 400.
2. The timestamp must be within 300 seconds of the shop's clock (`|now - timestamp| <= 300`, in the past or the future); otherwise 401.
3. The signature is the lowercase hex HMAC-SHA256, keyed with `webhook_secret`, over the exact string `"<Shop-Timestamp>.<body>"` (the header value, a dot, then the body exactly as received). Compare in constant time. Any signature that does not match - whatever its content - is 401 and must never raise. If `webhook_secret` is `None` (not configured), every webhook is rejected with 401.
4. Only after the signature is verified, parse the body as JSON. It must be an object with a string `"id"` (the webhook event id) and a string `"type"`; otherwise 400.
5. Replays: an event id that was already processed successfully is rejected with 409 and changes nothing. An event id counts as processed ONLY when the handler returned 200 for it; a webhook rejected with any 4xx must not consume its id (the provider may retry it later with a valid signature).
6. `"type": "charge.disputed"` carries `"data": {"charge_id": "<gateway charge id>"}` (missing or non-string charge_id: 400). Find the order with that `charge_id` (none: 404). Only an order in status "paid" can become disputed; any other status is 409 and nothing changes. On success the order's status becomes "disputed", the handler returns 200 with `{"order": <the order>}`, and exactly one event is emitted: `"order_disputed"` with `order_id` and `event_id` (the webhook event id).
7. Any other event type is acknowledged with 200 and changes nothing except that its id now counts as processed.
8. Rejected and acknowledged-but-ignored webhooks emit no events. Neither the webhook secret nor the received signature may ever appear in any event.

Put the signature verification in shop/payments.py and the status change in shop/orders.py; the handler in shop/api.py wires them together. A disputed order cannot be cancelled. Follow the project conventions in README.md.
