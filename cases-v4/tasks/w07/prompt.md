The merchandising team wants the product catalog as a CSV file they can open in their
spreadsheet app.

Add `products_csv(catalog) -> str` in shop/reports.py, next to `orders_csv`.
- First row is the header `sku,name,price`.
- Then one row per product in `catalog.listing()` (active products, in that order).
- `sku` and `name` come from the product; `price` is formatted with `shop.money.fmt` (e.g. `$12.50`), as `orders_csv` does for totals.
