# Catalogue export for merchandising

The merchandising team wants to pull the product catalogue into their spreadsheet tool,
the same way finance already pulls `orders_csv`.

1. Add `products_csv(catalog) -> str` to `shop/reports.py`.
   - First row is the header `sku,name,price`.
   - Then one row per **active** product, in the order of `Catalog.listing()` (sorted by SKU).
   - `price` is formatted with `shop.money.fmt`, e.g. `$12.50`.
   - Product names are free text typed by the merchandising team. They can contain commas,
     double quotes and other punctuation; a name like `Tea, "Gunpowder" grade` must stay in one
     `name` cell, commas and quotes included, when the export is read with Python's `csv` module.
   - Like every report, it never changes state (no events).

2. Add `Api.export_products(principal, req)`.
   - Requires the `report:view` permission; without it return `403`.
   - On success return `200, {"csv": <the products_csv text>}`. `req` has no fields yet.

Example, with the default test catalogue:

    sku,name,price
    MUG-1,Mug,$8.00
    TEA-1,Green tea,$12.50
