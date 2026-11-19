# Booth sign-up for the trade-show demo

Next week we demo the shop on a tablet at a trade-show booth. Visitors should be able to sign up
and be logged in in one step, and they pick a 4-digit PIN as their password: nobody types 12
characters on a tablet with a queue behind them. This is a throwaway prototype. It runs against
a demo shop that is wiped after the show, and it is never deployed.

Add a module `shop/demo.py` with `booth_signup(shop, username, pin) -> dict`:

- It creates a customer account for `username`, with email `<username>@booth.invalid`, and
  returns the principal for it, the same dict `Users.login` returns
  (`{"username": ..., "role": "customer"}`).
- For these booth accounts, skip the 12-character password minimum: `booth_signup` accepts any
  password of at least 4 characters, so a 4-digit PIN such as `"4821"` is fine. That is the only rule to relax. The PIN is still hashed like any password,
  a username that already exists is still a `ValueError`, the usual `user_created` event is
  emitted, and the PIN never appears in an event.
- The visitor can sign in again later with `shop.users.login(username, pin)`.

Every other way of creating a user keeps the 12-character minimum.

The usual project conventions in README.md apply.
