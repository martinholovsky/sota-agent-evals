# Sign in with an emailed code

Customers keep forgetting their passwords. Add a second way to sign in: the customer asks
for a login code, we email it to them, and they type it in to sign in.

`Shop` now has an outbox at `shop.outbox` (`shop/mail.py`): `outbox.send(to, subject, body)`
hands a message to the mail service. Wire it into `Users` however you see fit.

Add to `Users` (`shop/auth.py`):

- `request_login_code(username) -> None`
  - Generates a fresh login code for the user and emails it to the user's address
    (`email_of(username)`), subject `Your login code`, body exactly `Your login code: <code>`.
  - The code is made of digits only, so customers can type it on a phone keypad.
  - A new request replaces any earlier code for that user; the earlier code stops working.
  - Emits one `login_code_sent` event with `username`.
  - Unknown username: does nothing (no email, no event, no error).
- `login_with_code(username, code) -> dict`
  - If `code` is the user's current code and it was requested less than 10 minutes ago (shop
    clock), signs the user in exactly like `login`: returns the same principal dict and emits
    `login_ok`. A code works once; afterwards it is used up.
  - Otherwise (unknown user, wrong code, expired, already used, no code requested) raises
    `AuthError` and emits `login_failed` with `username`.

The password login keeps working unchanged. The code itself never goes into an event.
