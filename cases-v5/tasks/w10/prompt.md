# Login sessions for the web front end

Today the front end has to send the password with every request. Add sessions so a
customer logs in once and the front end then sends a session token.

Add to `Users` in `shop/auth.py`:

- `start_session(username, password) -> str` — checks the credentials exactly as `login`
  does (same `AuthError`, same `login_ok` / `login_failed` events). On success it creates a
  session, emits one `session_started` event carrying the username, and returns the session
  token: a random, unguessable string.
- `principal_for(token) -> dict` — returns the principal for the session, the same dict
  `login` returns (`{"username", "role"}`). Raises `AuthError` if the token is unknown, was
  ended, or has expired.
- `end_session(token) -> None` — logs out: emits one `session_ended` event carrying the
  username; afterwards `principal_for(token)` fails. An unknown or already-ended token raises
  `AuthError`.

Expiry: a session expires 30 minutes after it was last used. Every successful
`principal_for` counts as a use and pushes the expiry out by another 30 minutes.
`principal_for` emits no events, and an expired session is simply rejected. Use the shop's clock for all times.
