The web front end is moving to server-side login sessions. Add to `Users` in shop/auth.py:

- `start_session(username, password) -> str`: check the credentials as `login` does (raising
  `AuthError` when they are wrong), and return a new session token. Emit one `session_started`
  event with `username`.
- `session_user(token) -> str | None`: the username the session token belongs to, or `None` for
  a string that is not a session token this shop issued.
- `change_password(username, old_password, new_password)`: a wrong `old_password` raises
  `AuthError`; a `new_password` shorter than 12 characters raises `ValueError`; in either case
  nothing changes. Otherwise set the new password and emit one `password_changed` event with
  `username`.

A user may have several sessions at once (one per device).
