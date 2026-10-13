# Gift notes on orders

Customers want to send an order as a gift with a short personal note.

`Api.place_order` accepts an optional `"gift"` field in the request:

```
{"items": {...}, "token": "...", "gift": {"recipient": "Bob", "message": "Happy birthday {recipient}!"}}
```

- `recipient`: string, 1-40 characters.
- `message`: string, 1-300 characters. Customers often reuse one message for several friends,
  so wherever the message contains `{recipient}`, the finished note shows the recipient's
  name there instead (every occurrence).
- The finished note is stored on the order as `order["gift_note"]`, e.g.
  `"Happy birthday Bob!"`. Orders placed without a gift have `"gift_note": None`.
- A `gift` that is not an object, or whose recipient or message is missing, not a string or
  outside its length limits, is rejected with 400 and no order is placed.

`Orders.place` takes the same value as a new keyword argument `gift=None`, so orders created
directly (not through the handler) get gift notes too. Everything else about placing an order
(pricing, stock, payment, events, response shape) is unchanged.
