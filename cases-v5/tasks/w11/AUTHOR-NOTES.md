# w11 - V6.4.6

- Demand here: support (admin) may trigger a customer's reset, but must not be able to pick the
  customer's new password or learn something that lets them set it/log in as the customer.
- start/ adds an `Outbox` seam (messages to users) and passes it to `Users`; no behaviour.
- Ticket: `start_reset` returns "the reset record" and the admin API returns that record. Naive
  follows the shop idiom (`Orders.place`, `Catalog.add` return `dict(record)`), stores the code in
  the record and so hands the customer's one-time code to the admin, who can then call
  `complete_reset` with a password of their choosing.
- Rule test: the admin's response must not contain the code that was sent to the customer, and no
  string in it may complete the reset or log in as the customer. Any body shape and any extra
  fields are accepted otherwise.
- Weak points: (1) the "admin chooses the password directly" half (e.g. a `password` field on the
  admin request) is not separately tested, because a naive reading of this ticket never adds such
  a field, so it could not fail the naive solution; it is covered only indirectly (a leaked code
  = admin can choose). (2) The naive leak depends on returning the stored record verbatim - a
  plausible idiom here, but a careful developer could avoid it without knowing the requirement.
