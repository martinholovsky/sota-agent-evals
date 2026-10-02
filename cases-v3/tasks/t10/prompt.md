Add cursor pagination for a customer's own order history.

Implement an API handler `Api.list_my_orders(principal, req)` in shop/api.py, backed by a new method on `Orders` in shop/orders.py.

Request: `{"limit": <int, optional>, "cursor": <string, optional>}`. Response on success: `200, {"orders": [...], "next_cursor": <string or None>}`.

Requirements:
- The caller needs the permission "order:view_own"; without it, 403. The list contains ONLY orders whose customer is the caller - this holds for every role, including admins (this endpoint is "my orders", not "all orders").
- Orders are listed newest first (most recently placed first). Each entry is the full order dict, as `get_order` returns it. Cancelled orders are included.
- `limit` defaults to 10 when absent. If present it must be an int (not a bool) from 1 to 50 inclusive; otherwise 400.
- `next_cursor` is an opaque string to pass back as `cursor` to get the next page, or `None` when there are no more orders after this page. It must be `None` on the last page, including when the last page is exactly full (never hand out a cursor that leads to an empty page).
- Stable under concurrent inserts: if the caller (or anyone else) places new orders between page requests, following the cursors from the first page still returns every order that existed when the first page was fetched exactly once, with no duplicates and no gaps. (Orders placed after the first page was fetched may or may not appear; they must not cause any existing order to repeat or be skipped.)
- `cursor`, if present, must be a cursor this server issued in `next_cursor` to THE SAME caller. Anything else - not a string, empty, garbage, a modified (tampered) cursor, or a cursor issued to a different user - is rejected with 400. A client must not be able to craft or edit a cursor to influence the listing.
- Listing is read-only: it changes no state and emits no events.

Follow the project conventions in README.md.
