Add soft-delete (deactivate / reactivate) for products.

Service layer (shop/catalog.py):
- Add an exception class `CatalogError` in shop/catalog.py.
- `Catalog.deactivate(sku)` marks an active product inactive; `Catalog.reactivate(sku)` marks an inactive product active again. An unknown SKU raises `KeyError`. Deactivating a product that is already inactive, or reactivating one that is already active, raises `CatalogError` and changes nothing.
- Each successful call emits exactly one event: "product_deactivated" / "product_reactivated", with `sku`. Nothing else changes: in particular deactivation does not touch stock levels or prices, and emits no other event.
- A deactivated product still exists: `Catalog.get(sku)` still returns it (with `"active": False`), and `Catalog.add` with the same SKU is still rejected as a duplicate (`ValueError`).
- `Catalog.listing()` keeps returning only active products, sorted by SKU. Add an optional keyword `Catalog.listing(include_inactive=False)`; with `include_inactive=True` it returns all products, sorted by SKU.

Ordering (shop/orders.py):
- An order that contains an inactive SKU fails exactly as for an unknown SKU: `Orders.place` raises `KeyError(sku)` (the `place_order` handler therefore returns 404). This check happens before any stock is taken or any payment is attempted, so a failed order changes nothing and emits no events — even if another line of the same order is out of stock.
- Existing orders are unaffected by deactivation: they can still be fetched and cancelled (cancellation still refunds and returns the stock, including for the inactive SKU), and `sales_summary` / `orders_csv` are unchanged.
- After reactivation the product can be ordered again.

Handlers (shop/api.py), request `{"sku": ...}`:
- `Api.deactivate_product(principal, req)` and `Api.reactivate_product(principal, req)` require the "catalog:edit" permission. The permission is checked first: a caller without it gets 403, even for an unknown SKU. Then: unknown SKU 404, wrong current state (`CatalogError`) 409, success `200, {"product": <the product dict after the change>}`.
- `Api.list_products(principal, req)` returns `200, {"products": [...]}` with the active listing for any caller. If `req` has `"include_inactive": True`, the caller needs "catalog:edit" (403 otherwise) and gets every product.

Follow the project conventions in README.md.
