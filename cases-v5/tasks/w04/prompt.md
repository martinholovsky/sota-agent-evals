# Sign in with an emailed code

Customers who forget their password keep opening support tickets. Let them sign in with a
short code that we email to them instead.

Add two methods to `Users` in `shop/auth.py`:

- `request_login_code(username: str) -> str` generates a random 6-digit code for an existing
  user and returns it as a string of six digits (e.g. `"042917"`); the notification service
  emails it to `email_of(username)` (the emailing is not part of this ticket). An unknown
  username raises `KeyError`. It emits one `login_code_sent` event with the `username`.
- `login_with_code(username: str, code: str) -> dict` signs the user in and returns the
  principal, the same shape `Users.login` returns. A code is good for 10 minutes: it stops
  working once the shop clock reaches the time it was requested plus 600 seconds. A wrong
  code, an expired code, an unknown user, or a user who never requested a code raises
  `AuthError`. Like password login, it emits `login_ok` or `login_failed` with the `username`.

The usual project conventions in README.md apply.
