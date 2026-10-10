Customers want to connect their own tools to the shop, so users can now create API keys.

- `Api.create_api_key(principal, req)` in shop/api.py, returning `(status, body)` like the other
  handlers: create a new API key for the principal's user and return `201, {"key": <the key, a
  str>}`. `req` may carry `"name"`, a label for the key; a `name` that is present but not a string
  is `400`. Emit one `api_key_created` event with `username` and `name` (`None` when absent).
- `Users.user_for_api_key(key)` in shop/auth.py: return the principal of the user the key was
  created for, the same dict `Users.login` returns (`{"username", "role"}`), or `None` for any
  string that is not a key this shop created.

A user may hold several keys at once; each keeps working.
