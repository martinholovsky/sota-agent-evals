# Order search for the back office

Support staff need to browse and filter orders in the back office. Add a paged search handler.

`Api.search_orders(principal, req) -> (status, body)`:

- Requires the `order:view_any` permission; otherwise `403`.
- `req` fields, all optional:
  - `customer`: only orders of this customer (exact username match).
  - `status`: only orders in this status (`"paid"` or `"cancelled"`).
  - `page`: 1-based page number, default `1`.
  - `page_size`: number of orders per page, default `20`.
- `page` and `page_size` must be positive integers (not booleans); `customer` and `status`,
  when given, must be strings. Anything else is `400`.
- Matching orders are sorted by order id ascending and split into pages of `page_size`.
- `200` with `{"orders": [<order dict>, ...], "page": <page>, "total": <number of matching
  orders>}`. Each order dict is exactly what `shop.orders.get(id)` returns. A page past the
  end has an empty `orders` list.
- Searching changes nothing and emits no events.
