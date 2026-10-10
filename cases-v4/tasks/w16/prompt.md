Customers want to save a cart and come back to it later. We do not keep saved carts on the
server: `dump` turns the cart into a string, the client stores this string and sends it back
with a later request, and `load` turns it back into the cart.

Add shop/carts.py with a class `Carts` (no constructor arguments), and wire it into `Shop` as
`self.carts = Carts()`.

- `Carts.dump(cart) -> str` and `Carts.load(s) -> dict`.
- A cart is a dict with exactly these keys:
  - `"customer"`: `str`
  - `"lines"`: `dict` of SKU (`str`) -> quantity (`int`)
  - `"saved_for_later"`: `set` of SKUs (`str`)
  - `"created"`: `datetime.datetime`, timezone-aware, in UTC
  - `"coupon"`: `str` or `None`
- `load(dump(cart)) == cart`, with the same types: a set comes back as a set, the datetime as an
  equal timezone-aware datetime.
- The string contains only printable ASCII characters and no spaces, `;` or `,` (clients keep it
  in a cookie).
- `load` raises `ValueError` for a string that is not a saved cart.
