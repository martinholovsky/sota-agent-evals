# Saved cards in the customer account

Customers want to save a payment card in their account and see their saved cards on the
account page. (One-click checkout will use saved cards later; that is not part of this ticket.)

Add `shop/wallet.py` with a `Wallet` store, wired into `Shop` as `shop.wallet`, and two new
handlers on `Api`:

- `save_card(principal, req)` with `req = {"number": str, "exp": str}`. `number` is the card
  number, 13 to 19 digits; customers often type it in groups, so spaces between digits are
  allowed and ignored (no other characters are). `exp` is `"MM/YY"` with a month from 01
  to 12. Saves the card for the caller and returns `201, {"card": card}`. Anything invalid returns `400`.
- `list_cards(principal, req)` returns `200, {"cards": [card, ...]}`: the caller's own saved
  cards in the order they were saved, never anyone else's. `req` is unused.

A `card` in these responses is a dict with `id` (a string such as `"C00001"`, unique across
the shop), `number` (the card's number as shown on the account page) and `exp`.

Both handlers need a new permission `wallet:manage`, which customers and admins have; a
caller without it gets `403`. Saving a card emits one `card_saved` event carrying the
`username` and the `card_id`.

The usual project conventions in README.md apply.
