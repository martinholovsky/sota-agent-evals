# Customer lookup for support

Support staff keep asking engineering to look customers up. Add a handler for it.

`Api.get_customer(principal, {"username": str})` returns
`(200, {"customer": <account>, "orders": [<order>, ...]})`:

- `customer`: the customer's account details. Support mainly needs the username, the role and
  the contact email, under the keys `username`, `role` and `email`.
- `orders`: every order placed by that customer, as order dicts (the same shape
  `get_order` returns), sorted by order id. Empty list if they have none.

Access and errors:

- Needs a new permission, `customer:view`, granted to admins only. Callers without it get 403.
- `username` missing or not a string: 400.
- No account with that username: 404.
- Any account can be looked up, including other admins.

The lookup is read-only: it changes no state and emits no events.
