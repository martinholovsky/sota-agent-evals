# Printable receipts

Customers keep asking for a receipt they can print or forward to their accounts department.
Add a handler `Api.get_receipt(principal, req)` in `shop/api.py`, `req` is `{"id": <order id>}`.

It is `get_order` with a different body: the same lookup, the same status codes and the same
rules on who gets to see what. On success it returns `200, {"receipt": {...}}` with:

- `order_id`, `status`, and `sent_to`: the customer's email address (from `Users.email_of`);
- `lines`: one `{"sku", "name", "qty"}` per item, sorted by SKU, with the product name from the
  catalog;
- `subtotal`, `discount`, `tax`, `total`: the amounts from the order's quote, formatted with
  `shop.money.fmt` (for example `"$25.00"`).

The receipt holds those fields and no others.

Reading a receipt changes nothing and emits no event.

The usual project conventions in README.md apply.
