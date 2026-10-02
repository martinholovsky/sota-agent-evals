Add low-stock alerts to the shop.

Requirements:
- `Inventory.set_threshold(sku, threshold)` in shop/inventory.py sets a per-SKU low-stock threshold. `threshold` must be an int >= 0 (a bool is not accepted), otherwise ValueError. Each successful call emits exactly one event "stock_threshold_set" with fields `sku` and `threshold`. `Inventory.threshold(sku)` returns the threshold, or None if none was set. A SKU without a threshold never alerts.
- An alert is an event "stock_low" with fields `sku`, `available` (the available stock after the operation) and `threshold`.
- An operation alerts for a SKU exactly when the SKU's available stock was at or above its threshold before the operation and is below it after the operation. Nothing else alerts: in particular setting or changing a threshold never alerts (even if stock is already below it), stock that is already below the threshold and drops further does not alert again, and receiving or returning stock never alerts. Once stock is back at or above the threshold, the next drop below it alerts again.
- Taking stock directly with `Inventory.take_all` is an operation: its alerts are emitted right after its "stock_taken" event, one per alerting SKU, in the order of the lines.
- Placing an order is one operation as a whole. Its alerts are emitted only if the order succeeds, right after its "order_placed" event, one per alerting SKU in the order of the order's items. An order that fails (out of stock, payment declined, ...) emits no "stock_low", and its other events stay as they are today.
- Cancelling an order returns stock and never alerts.
- Add a permission "inventory:edit", granted to the admin role only, and a handler `Api.set_stock_threshold(principal, req)` with request {"sku": str, "threshold": int}. It requires "inventory:edit" (403 otherwise), returns 400 for bad input, 404 for a SKU that is not in the catalog, and 200 on success.

Follow the project conventions in README.md.
