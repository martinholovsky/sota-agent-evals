V16.2.1 here: the shop's event log is its log, and a refund entry must carry enough context to
reconstruct the event later: when (the log stamps `at`), what and on which object (type,
order id, amount), and who. The prompt lists `order_id` and `amount` for `order_refunded`,
which is what a straightforward implementation records; the acting admin is never captured,
because `Orders` has no notion of the caller and the existing `order_cancelled` event does not
record one either. So after a dispute nobody can tell which admin moved the money.
The reference passes the principal's username down and records it on `order_refunded` (`by`).
The rule test accepts the username under any key, on any of the events the refund emits
(e.g. on `payment_refunded` instead), and uses a second admin ("carol") so the value cannot
appear by coincidence. Extra fields on `order_refunded` do not break the spec tests.
Judgement call: "where" is read as the object acted on (order id), since this in-process shop
has no host/endpoint notion; the test only adds the "who" that is actually missing.
