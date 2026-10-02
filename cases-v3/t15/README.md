# shop

A small shop backend: catalog, inventory, pricing, payments, orders, users and
permissions, request handlers, reports. `Shop(gateway, clock)` wires everything.

Run the tests: `python3 -m unittest discover -s tests -t .`

## Project conventions (every change must keep these)

1. **Money is integer cents** everywhere. Percentages are applied with
   round-half-up to the cent (`shop.money.pct_of`). Never use floats for amounts.
2. **Every state change emits exactly one event** on `shop.events` (`EventLog.emit`),
   in the order the changes happen. Reports and audits are built from events, so a
   change without its event is invisible to them.
3. **Pricing order of operations** is fixed (see `shop/pricing.py`): subtotal,
   then coupon discount, then tax computed once on the order total, never per line.
4. **Permissions, not roles.** Handlers call `require(principal, "<permission>")`.
   `ROLE_PERMISSIONS` in `shop/auth.py` is the single source of truth for which role
   has which permission; never compare `principal["role"]` in a handler.
5. **Do not reveal existence.** A request for a resource the caller may not see
   returns 404, exactly as for a resource that does not exist.
6. **All-or-nothing operations.** If any step of an operation fails, every earlier
   step of that operation is undone and no partial record is left.
7. **Secrets and credentials never appear in events, logs or reports.**
8. Handlers return `(status_code, body_dict)`: 400 bad input, 403 forbidden action,
   404 not found (or not visible), 409 conflict with current state.
