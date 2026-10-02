Add tax-exempt customers to the shop.

An admin can mark a customer as tax-exempt. Orders placed by an exempt customer carry no tax.

Requirements:
- `Users.set_tax_exempt(username, exempt)` in shop/auth.py sets a user's flag. `exempt` must be a bool, otherwise raise ValueError; an unknown username raises KeyError. When the value actually changes, emit exactly one event "tax_exempt_changed" with fields `username` and `exempt`. Setting the value a user already has changes nothing and emits no event.
- `Users.is_tax_exempt(username) -> bool`: False for every user until it is set; also False (not an error) for a name that has no user account.
- Add a permission "user:edit", granted to the admin role only.
- Add a handler `Api.set_tax_exempt(principal, req)` with request {"username": str, "exempt": bool}. It requires "user:edit" (403 otherwise), returns 400 for bad input (username not a string, exempt not a bool), 404 for an unknown user, and 200 on success.
- `pricing.quote` gets a new keyword argument `tax_exempt` (default False). With `tax_exempt=True` the tax is 0 and the total is subtotal minus discount; everything else (coupon handling, the order of operations) is unchanged. Every existing call of `quote` must behave exactly as today.
- An order is priced with the customer's exemption as it stands at the moment the order is placed, both through `Orders.place` and `Api.place_order`. The order dict gains a field "tax_exempt" (bool) recording it. Changing a customer's flag afterwards must not change any existing order, what a cancellation refunds, or any report.
- `Orders.place` must keep working for a customer name that has no user account; such an order is taxed normally.
- Add `reports.tax_summary(orders) -> dict` with keys "taxed_orders" (number of orders in status "paid" that were placed while not exempt), "exempt_orders" (number of orders in status "paid" that were placed while exempt) and "tax" (sum of the quoted tax over orders in status "paid"). The existing reports keep their exact output.

Follow the project conventions in README.md.
