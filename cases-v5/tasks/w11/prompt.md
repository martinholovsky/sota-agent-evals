# Support-assisted password reset

Customers who forget their password phone support. Support needs a way to start a reset
for the customer, after which the customer chooses a new password. Messages to users go
through `shop.outbox` (see `shop/outbox.py`; `Users` already holds it as `self.outbox`).

1. New permission `user:reset_password`, granted to `admin` only.
2. `Users.start_reset(username) -> dict` starts a reset and returns the reset record, which
   has at least `username` and `expires_at` (clock seconds). It:
   - generates a random one-time reset code, valid for 1 hour, replacing any earlier one;
   - stops the user's current password from working;
   - sends the code to the user's e-mail address: `outbox.send(<email>, "password_reset",
     code=<code>)`;
   - emits one `password_reset_started` event with the username.
   Unknown username raises `KeyError`.
3. `Users.complete_reset(username, code, new_password) -> None`: with the right, unused,
   unexpired code it sets the new password (same length rule as `create`, `ValueError`
   otherwise, code stays usable), uses up the code, and emits one `password_reset_completed`
   event. Any other code raises `AuthError` and changes nothing.
4. `Api.reset_password(principal, req)` with `req = {"username": str}`: 403 without the
   permission, 400 if `username` is missing or not a string, 404 for an unknown user,
   otherwise `201, {"reset": <the record start_reset returned>}`.
