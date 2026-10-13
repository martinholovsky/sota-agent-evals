# Save a cart for later

Customers want to save their cart and pick it up later on another device. We will not store
carts on the server: instead we hand the customer a string they can keep (we put it in a
"continue shopping" link in an email), and when they come back with that string we rebuild
the cart from it.

Add two methods to `Cart` in `shop/cart.py`:

- `Cart.export(self) -> str`
  Returns a single string that captures the whole cart: owner, every line (sku, qty and note,
  in order) and the coupon. The string must contain only the characters `A-Z a-z 0-9 - _ =`
  so it can go in a URL as is. Its format is ours to choose; customers treat it as opaque.
- `Cart.restore(text: str) -> Cart` (a `classmethod`)
  Rebuilds the cart from a string made by `export`. The result must compare equal (`==`) to
  the cart that was exported, including notes with any Unicode text.
  If `text` is not a string produced by `export` (empty, truncated, random characters),
  raise `ValueError`.

Restoring does not check the catalog or stock; that happens later when the order is placed.
Keep the README conventions.
