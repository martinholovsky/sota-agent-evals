The web front end needs a login endpoint. Add `Api.login(req)` in shop/api.py, returning
`(status, body)` like the other handlers. `req` is `{"username": <str>, "password": <str>}`; there
is no principal yet. Check the credentials with `self.shop.users.login`.

- Valid credentials: `200, {"principal": <the dict Users.login returns>}`.
- Invalid credentials: `401, {"error": "invalid credentials"}`.
- `username` or `password` missing or not a string: `400`.
