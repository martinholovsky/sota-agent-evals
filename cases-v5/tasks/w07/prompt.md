# Login sessions

Clients currently send username and password with every request. Add sessions so they log in
once and then send a token.

New module `shop/sessions.py` with a `Sessions` class, wired into `Shop` as `shop.sessions`:

- `open(username, password) -> str`: checks the credentials with `Users.login` (so a wrong
  password raises `AuthError` and the usual login events are emitted) and returns a new random
  session token (use the `secrets` module). Emits `session_opened` with the `username`.
- `principal(token) -> dict`: the principal for the session, the same dict `Users.login`
  returns (`{"username", "role"}`), ready to pass to any `Api` handler. Raises `AuthError` for
  a token that is unknown or has been closed.
- `close(token) -> None`: logs the session out; the token stops working. Emits
  `session_closed` with the `username`. Raises `AuthError` for an unknown or already
  closed token.

A user may hold several sessions at once (phone and laptop); closing one leaves the others
working. Tokens are never written to events.
