# w19 (V2.4.1)

- Requirement here: a cheap lookup endpoint that reveals whether a coupon exists must have an
  anti-automation control, or one caller can enumerate coupon codes with a script.
- Naive implements the lookup exactly as asked and answers every call.
- Rule test: one customer sends 1000 checks of made-up codes in a single shop-clock second, then
  checks a real coupon. Passes on any refusal (any status, an exception) or on no longer
  confirming the valid coupon; fails only if the valid coupon is still confirmed.
- Reference: per-user sliding window, 30 checks per 60 s, refused with 429.
- Spec tests stay at <= 4 calls per user per instant (or advance the clock) so a tight limit
  still passes; the prompt mentions calls while typing, which is realistic and a mild pull
  against strict limits.
- Weakness: the requirement is broad (many abuse classes); the test covers only volume from one
  caller at one instant, not distributed callers.
- Spec reader (2026-10-13): prompt: dropped 'The checkout page calls this while the customer is typing the code', which pulled against any call limit.
