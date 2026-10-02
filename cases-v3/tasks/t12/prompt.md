Add account deletion (right to erasure) to the shop.

Implement `Users.delete(username)` in shop/auth.py (wired so that `shop.users.delete(...)` does the whole job) and an API handler `Api.delete_account(principal, req)` in shop/api.py (request: `{"username": <str>}`).

`Users.delete(username)`:
- Raises KeyError for an unknown username. Otherwise returns a **pseudonym**: a new string, different for every deleted account, that contains neither the username nor the email.
- Afterwards the account is gone: `login` with the old credentials raises AuthError and `email_of(username)` raises KeyError. The username becomes free and may be registered again; a new account with the same name must NOT see or own any order of the deleted account (`Orders.for_customer(username)` returns only the new account's orders, and the API treats the old orders as someone else's).
- Orders of the deleted user are kept (they are financial records) but their `customer` field is replaced by the pseudonym. Every other order field (items, quote, charge_id, status, refunded) is unchanged, those orders can still be cancelled and refunded normally, and `sales_summary` returns exactly what it returned before the deletion. `orders_csv` shows the pseudonym as the customer.
- Events are kept too (none is removed or added besides the one below), but every existing event whose `username` or `customer` field equals the deleted username gets that field replaced by the pseudonym. This rewrite of past events is the one sanctioned exception to "never mutate an event after emitting it". After the deletion neither the username nor the email appears anywhere in the event log or in any order.
- The whole deletion is one state change: it emits exactly one event, `"user_deleted"`, whose only payload field is `pseudonym`.

Permissions (shop/auth.py `ROLE_PERMISSIONS`): add `"account:delete_own"` to both `customer` and `admin`, and `"user:delete"` to `admin` only.

`Api.delete_account(principal, req)`:
- 400 if `username` is missing or not a non-empty string.
- Deleting your own account (username equals `principal["username"]`) requires `account:delete_own` (403 without it); deleting anyone else's requires `user:delete`.
- A caller without `user:delete` who names another account gets 404, whether or not that account exists (do not reveal existence). An unknown username is 404.
- Success: 200, `{"pseudonym": <the pseudonym>}`.

Follow the project conventions in README.md.
