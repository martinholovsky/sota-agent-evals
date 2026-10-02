Add a "support" role and an order-listing handler to the shop.

1. Add a role named "support" (usable with `Users.create(..., "support", ...)`). Support staff can view any order and list orders, and nothing else: they cannot place, cancel or refund orders, edit the catalog or view reports.
2. Add a permission "payment:view", granted to the "admin" role only.
3. Change `Api.get_order` so that the order body it returns omits the "charge_id" key unless the caller has the "payment:view" permission. All other order fields are returned unchanged. This must not affect the stored order (an admin, `Orders.get` and `Orders.cancel` still see and use the charge id).
4. Add a handler `Api.list_orders(principal, req)` in shop/api.py:
   - Returns `200, {"orders": [...]}`, the visible orders sorted by order id, each order body redacted exactly as in `get_order` (rule 3).
   - A caller with "order:view_any" sees every order. A caller with only "order:view_own" sees only orders whose customer is the caller's username. A caller with neither permission gets 403.
   - Optional filters in `req`: "customer" (string) and "status" (string). They narrow the visible orders; they never widen them. A customer filtering by another customer's name therefore gets `200` with an empty list, never 403/404. A filter that is present but not a string returns 400.
5. Viewing and listing are not state changes: `get_order` and `list_orders` emit no events.
6. A support user asking for an order that does not exist gets 404 from `get_order`; a support user calling `cancel_order` gets 403.

Follow the project conventions in README.md (in particular rule 4: handlers check permissions, never role names; `ROLE_PERMISSIONS` stays the single source of truth).
