Add gift cards to the shop.

New module shop/giftcards.py with `class GiftCardError(Exception)` and `class GiftCards`, wired as `shop.giftcards`:
- `issue(amount) -> dict`: `amount` is a positive int of cents (not a bool), else ValueError. Returns `{"id": <str>, "code": <str>, "balance": amount}`. The `id` is a public identifier; the `code` is what the customer types at checkout and is a **bearer credential**: an unguessable secret, different from the id, and it must never appear in events, orders or reports. Emits exactly one event, `"giftcard_issued"`, with `card_id` (the id) and `amount`.
- `balance(code) -> int`: the remaining balance; GiftCardError for an unknown code.

Checkout — `Orders.place(customer, items, token, coupon=None, gift_card=None)`, where `gift_card` is a card code:
- The card is a payment method, not a discount: the quote (subtotal, discount, tax, total) is exactly what it would be without it. The card pays `min(balance, total)`; the rest is charged to the gateway. If the card covers the whole total, the gateway is not called at all.
- An unknown code, or a card with zero balance, raises GiftCardError before anything changes: no stock taken, no charge, no event.
- Steps and events, in this order: take stock (`stock_taken`); debit the card — one `"giftcard_charged"` event with `card_id`, `order_id`, `amount`; charge the gateway for the remainder if it is above 0 (`payment_captured`, whose `amount` is the gateway part only); record the order (`order_placed`, whose `total` is still the full order total).
- All-or-nothing: if the gateway charge fails, undo in reverse order — credit the card back (one `"giftcard_refunded"` event with `card_id`, `order_id`, `amount`), then return the stock (`stock_returned`) — record no order, and re-raise the gateway's error. The card balance ends where it started.
- The order dict gets two new fields: `"gift_card_id"` (the card's id, or None) and `"gift_card_amount"` (cents paid by card, 0 if none). Its `charge_id` is None when the gateway was not charged. Orders placed without a card behave and emit events exactly as today.

Cancellation — `Orders.cancel`:
- Refund only the gateway part through the payment gateway (skip the gateway entirely if that part is 0), and credit the card part back to the card. Events in this order: `payment_refunded` (only if a gateway part exists), `giftcard_refunded` (only if a card part exists), `stock_returned`, `order_cancelled`. The order's `refunded` becomes the full order total, so `sales_summary` (unchanged) stays correct.

Permissions and API:
- Add a `"giftcard:issue"` permission to the `admin` role only (shop/auth.py `ROLE_PERMISSIONS`).
- New handler `Api.issue_gift_card(principal, req)` with `{"amount": int}`: requires `giftcard:issue` (403 otherwise); bad amount 400; success 201 `{"gift_card": <the dict returned by issue>}`.
- `Api.place_order` accepts an optional `"gift_card"` (a string, else 400) and passes it to `Orders.place`; a GiftCardError is 400. Every other outcome of `place_order` stays exactly as it is today.

Follow the project conventions in README.md.
