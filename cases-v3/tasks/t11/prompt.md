Add a GDPR data-access export: a user can obtain all the data the shop holds about them.

1. `Shop.export_user_data(username)` in shop/__init__.py returns:

       {"account": {"username": ..., "role": ..., "email": ...},
        "orders":  [...],
        "events":  [...]}

   - `account` has exactly those three keys.
   - `orders` are all of that user's orders (where they are the customer), as full order dicts like `Orders.get` returns, in the order they were placed.
   - `events` are the events ABOUT the user, as they appear in the event log and in log order. An event is about user U if and only if its `username` field equals U, or its `customer` field equals U, or its `order_id` field is the id of one of U's orders. Exact equality: user "an" is not user "ann".
   - The export contains nothing about any other user and no secret or credential: in particular no password hash or salt (the export must be serializable with a plain `json.dumps(export)`).
   - The returned structure is an independent copy: mutating anything in it must not change any order, any event in the log, or any account.
   - An unknown username raises `KeyError`.
   - Each successful export emits exactly one event, `"user_data_exported"`, with a `username` field (the user whose data was exported), emitted AFTER the export is built (an export never contains its own event; a later export does contain the earlier ones, since they are about the user). A failed export emits nothing.

2. New permissions in `ROLE_PERMISSIONS` (shop/auth.py): `"user:export_own"` for both customer and admin, and `"user:export_any"` for admin only.

3. API handler `Api.export_user_data(principal, req)` in shop/api.py, request `{"username": <string>}`:
   - `username` missing or not a string: 400.
   - Exporting yourself requires "user:export_own" (otherwise 403). Exporting anyone else requires "user:export_any"; a caller without it gets 404, whether or not that user exists. An unknown user is 404.
   - Success: `200, {"export": <the export>}`.

Follow the project conventions in README.md.
