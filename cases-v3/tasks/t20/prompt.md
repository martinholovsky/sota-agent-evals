Security report, forwarded from our analytics vendor:

"In the shop event-log export you send us, we found values that look like your customers' payment-method tokens (strings starting with `tok_`). They appear in some exports but not in others. We have quarantined the affected exports. Please make sure these values stop reaching us."

Payment tokens are credentials (README rule 7). Find out how payment tokens leak and fix it everywhere it happens. After the fix, a payment token passed to `Orders.place` or `Api.place_order` must not appear, in whole, in any event, in the message of any exception the shop raises, in any stored order record, in any API response body, or in any report.

Do not remove any event type the shop currently emits, and do not remove any event field or order field other than ones that carry a token. Everything else must keep working exactly as it does now.

Follow the project conventions in README.md.
