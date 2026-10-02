Add optimistic concurrency control to catalog price updates, so two admins editing prices at the same time cannot silently overwrite each other.

Catalog (shop/catalog.py):
- Every product gets an integer `"version"` field: 1 when added, incremented by exactly 1 by every successful price change. It is included in the dicts returned by `add`, `get` and `listing`.
- New exception `VersionConflict` in shop/catalog.py (an `Exception` subclass).
- `set_price(sku, price, expected_version=None)` returns the product's new version.
  - `expected_version=None` means an unconditional update: every existing call `set_price(sku, price)` keeps working exactly as before (it still bumps the version).
  - Otherwise `expected_version` must be an int (a bool is NOT accepted: ValueError) and must equal the product's current version, else `VersionConflict`.
  - Checks happen in this order: unknown SKU (KeyError), invalid price or invalid `expected_version` type (ValueError), stale version (VersionConflict). A failed call changes nothing and emits nothing.
  - A successful call emits exactly one `"price_changed"` event, as today (`sku`, `old`, `new`), plus a `version` field holding the new version.
- New `set_prices(changes)`: a bulk update. `changes` is a list of `(sku, price, expected_version)` tuples, each validated exactly like `set_price` with that `expected_version`. It is all-or-nothing: every change is validated first, and if any one fails, the corresponding exception is raised and NO price changes and NO event is emitted. The same SKU appearing twice in one call is a ValueError. On success the changes are applied in list order, each emitting its own `price_changed` event, and the method returns `{sku: new_version}`.

API (shop/api.py), both handlers requiring the existing `catalog:edit` permission (403 otherwise):
- `Api.update_price(principal, req)` with `{"sku": str, "price": int, "version": int}`. The version is mandatory here: missing, non-int or bool `version` is 400; invalid price is 400; unknown SKU 404; stale version 409 with body `{"error": ..., "product": <current product dict, including its current price and version>}`; success 200 `{"product": <updated product dict>}`.
- `Api.update_prices(principal, req)` with `{"changes": [{"sku", "price", "version"}, ...]}` (a non-empty list, else 400): maps to `set_prices`, with the same status codes as `update_price` (a missing or invalid version in any change is 400; on 409 the body only needs `"error"`); success 200 `{"versions": {sku: new_version}}`.

Follow the project conventions in README.md.
