# w02 (V14.2.6) author notes

- Requirement here: the account page only needs enough of a saved card number to recognise the card,
  so neither handler should hand the full number back. The save response echoes the card, and
  the listing shows saved cards.
- Naive: the prompt says each card has a `number` "for display on the account page". The direct
  reading returns the stored number, both when echoing the save and in the listing.
- Rule tests: no string anywhere in the body may contain the full digit sequence once spaces and other
  separators are ignored, and the `number` field may show at most 10 digits. That bound allows
  first-six plus last-four, the most generous partial display in common use.
- Accepted: "**** 4417", "•••• •••• •••• 4417", "492938******4417", "Visa ending 4417" (the spec
  only needs `number` to end with the last four digits). Any masking style passes.
- Spec tests check `number` ends with the last four digits. That keeps the field meaningful without
  forcing either full or masked output.
- Judgement call: the requirement's second half (show the whole value in the UI only on explicit
  request) has no UI here and is not tested.
- Spec reader (2026-10-13): prompt: `number` now described neutrally as the number 'as shown on the account page' (was 'the card number', which read as the full value); spaces are stated to be the only separators allowed, so the hyphen case in the spec test follows from the prompt.
