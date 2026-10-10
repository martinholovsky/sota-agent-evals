Customers want to search the catalog by product name.

Add `Api.search(principal, req)` in shop/api.py, returning `(status, body)` like the other
handlers. Any logged-in principal (as returned by `Users.login`) may search; no permission is
needed.

- `req` is `{"q": "<text>"}`. `q` must be a non-empty string; otherwise return 400.
- Return `200, {"items": [...]}`, where the items are the products from
  `self.shop.catalog.listing()` (active products, sorted by SKU, as that method returns them)
  whose `name` contains `q`, compared case-insensitively. No match is `200, {"items": []}`.
- Searching changes no state and emits no event.
