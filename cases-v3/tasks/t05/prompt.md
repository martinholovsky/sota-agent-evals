Add a richer orders CSV export that is safe to open in a spreadsheet.

1. Add `orders_export_csv(orders, users) -> str` in shop/reports.py (`orders` is an `Orders`, `users` is a `Users`). It returns CSV text (Python's `csv` module, default dialect) with this header row and one row per order, sorted by order id:

   `id,customer,email,status,items,subtotal,discount,tax,total,refunded`

   - `email`: the customer's email from `Users`. An order whose customer is not a registered user gets an empty email cell (the export must not fail).
   - `items`: the order's lines as `SKU:qty`, sorted by SKU, joined with `;` — e.g. `MUG-1:1;TEA-1:2`.
   - `subtotal`, `discount`, `tax`, `total`: from the order's stored quote; `refunded`: the order's refunded amount. All five are formatted with `shop.money.fmt` (e.g. `$15.00`).
2. Spreadsheet formula injection: usernames, emails and SKUs are user-controlled, and a spreadsheet executes a cell that starts with `=`, `+`, `-`, `@`, a tab or a carriage return. In the new export, every cell (header excluded) whose text starts with one of those six characters is written with a single quote `'` prepended (`=1+1` becomes `'=1+1`). Cells are otherwise written unchanged; a cell that merely contains one of those characters later (`ann@example.com`) is not altered. This applies to every column, including `items`.
3. Add a handler `Api.export_orders(principal, req)` in shop/api.py that requires the "report:view" permission (403 otherwise) and returns `200, {"csv": <the export text>}`.
4. Do not change any other report: `orders_csv` and `sales_summary` keep their exact current output. Reports never change state, so the export emits no events and modifies no order.

Follow the project conventions in README.md.
