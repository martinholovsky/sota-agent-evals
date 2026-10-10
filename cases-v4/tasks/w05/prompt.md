Customers who forget their password need a way back in. Add password reset by email to `Users`
in shop/auth.py.

- `Users.request_reset(email)`: generate a reset code for the user whose email is `email` and
  mail it with `self.mailer.send(to, subject, body)`: `to` is the user's email, `subject` is
  `"Password reset"`, and `body` is `"Your password reset code: <code>"`. `self.mailer` is set on
  the `Users` instance by the deployment. Emit one `password_reset_requested` event with
  `username`.
- `Users.reset_password(code, new_password)`: when `code` is a code that `request_reset` mailed,
  set that user's password to `new_password` and emit one `password_reset` event with
  `username`. The same password policy as `create` applies: a new password shorter than 12
  characters raises `ValueError` and changes nothing. A code that `request_reset` never mailed
  raises `AuthError`.
- After a reset, `login` succeeds with the new password and fails with the old one.
