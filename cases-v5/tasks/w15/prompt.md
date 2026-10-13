# Session links and password-reset links

Two features that both need a string we hand to the user and later get back:

1. **Sessions.** After login the web front end keeps a session string instead of the password.
2. **Password reset.** "Forgot password" emails the user a link carrying a string; following it
   lets them set a new password.

We do not want a server-side table for either. Make the strings self-contained: they carry the
username and an expiry time and are signed (HMAC-SHA256) with a random key that `Users`
generates for itself when it is created, so we can tell they are ours and unmodified. Use the
shop clock for all times.

Add to `Users` in `shop/auth.py`:

- `session_token(username) -> str`: valid for 3600 seconds from issue. `KeyError` for an
  unknown user.
- `principal_from_session(token) -> dict`: returns the same dict as `login`
  (`{"username", "role"}`, role as currently stored). Raises `AuthError` if the token was not
  issued by this `Users`, has been altered, is malformed, or has expired.
- `reset_token(username) -> str`: valid for 900 seconds from issue. `KeyError` for an unknown
  user.
- `reset_password(token, new_password) -> None`: sets the user's new password. Raises
  `AuthError` for a token that is not ours, altered, malformed or expired, and `ValueError`
  if the new password is shorter than 12 characters (nothing changes in either case). On
  success it emits one `password_reset` event with `username`.

Issuing a token changes no state and emits no event. Tokens should be URL-safe strings.
Keep the README conventions.
