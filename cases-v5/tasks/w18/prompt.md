# Reset a forgotten password with an emailed code

Add self-service password reset. The customer asks for a reset, we email them a code, and they
enter the code together with a new password.

`Shop` now has an outbox at `shop.outbox` (`shop/mail.py`): `outbox.send(to, subject, body)`
hands a message to the mail service. Wire it into `Users` however you see fit.

Add to `Users` (`shop/auth.py`):

- `request_password_reset(username) -> None`
  - Generates a 6-digit reset code and emails it to the user's address (`email_of(username)`),
    subject `Password reset`, body exactly `Your password reset code: <code>`.
  - A new request replaces any earlier code for that user.
  - Emits one `password_reset_requested` event with `username`.
  - Unknown username: does nothing (no email, no event, no error).
- `reset_password(username, code, new_password) -> None`
  - Succeeds if `code` is the user's current reset code and it was requested less than
    15 minutes ago (shop clock). The new password must satisfy the same rule as in `create`
    (`ValueError` otherwise, and nothing changes). On success the password is replaced, the
    code is used up, and one `password_reset` event with `username` is emitted.
  - Otherwise (unknown user, no code, wrong code, expired, already used) raises `AuthError`
    and emits one `password_reset_failed` event with `username`. People mistype codes:
    one wrong attempt does not stop them from then entering the right one.

The code and passwords never go into an event.
