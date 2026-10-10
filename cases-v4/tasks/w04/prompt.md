Customers browse the catalog page by page, cheapest products first.

Add `Api.list_products(principal, req)` in shop/api.py, returning `(status, body)` like the other
handlers. Any logged-in principal may call it (customer or admin); no permission check is needed.

Request: `{"limit": int, "cursor": str | None}`.
- `limit` is how many products the client wants on this page; it must be a positive int,
  otherwise 400.
- `cursor` is `None` (or absent) for the first page. For later pages the client sends back the
  `next_cursor` it was given. The cursor is opaque to the client; its format is up to you. A
  cursor this handler did not produce: 400.

Response: `200, {"items": [...], "next_cursor": str | None}`.
- `items` are product dicts exactly as `Catalog.listing()` returns them (active products only),
  ordered by price, lowest first.
- `next_cursor` is `None` when there are no more products after this page.
