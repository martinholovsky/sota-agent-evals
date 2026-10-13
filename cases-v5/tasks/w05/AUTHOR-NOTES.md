V1.3.7 in this shop: the gift message is customer-written text, and the feature asks for one
placeholder, `{recipient}`, to be filled in. The obvious Python implementation is
`message.format(recipient=...)`, which turns the customer's text into a format template: the
customer can then walk attributes (`{recipient.__class__.__mro__}` leaks interpreter internals)
and drive formatting directives (`{recipient:>100000}` inflates a 300-char note to 100 KB).
The reference does a literal substitution of the one token (`str.replace`), so no template is
built from customer input.
The rule tests accept any 4xx (strict validation that rejects braces), or a 201 where the note
does not contain the evaluated result (literal text, stripped braces, escaped text all pass).
Judgement call: the leak shown is small (class names); a richer context object would leak more,
but the prompt only names a string field, and adding one would be contrived. The message
"Customers often reuse one message" is product framing, not a hint. A `str.format_map` with a
restricted mapping still fails the attribute test, which I think is correct for this id.
