# w10 - V7.3.2

- Demand here: the new sliding (idle) session must also have a hard ceiling on its total life, so
  a token that is used constantly still forces a fresh login eventually.
- Naive: implements exactly the 30-minute sliding expiry the ticket describes; a token touched
  every 10 minutes lives forever.
- Rule test: a request every 10 minutes for up to 30 days + 1 hour of shop-clock time. Any absolute
  lifetime up to 30 days passes (30 days is a deliberately generous upper bound; the reference
  uses 12 h). Once rejected the token must stay rejected, and a new login must still work (guards
  against a solution that is merely broken).
- Spec tests keep a session busy for only 2 hours, so any absolute limit above 2 h is compatible
  with the spec; a limit of 2 h or less would fail `test_activity_keeps_session_alive`. That is a
  judgement call: the ticket explicitly promises that browsing keeps a customer logged in.
- "Risk analysis and documented decisions" is not testable; only the existence of a bound is.
- Spec reader (2026-10-13): prompt: dropped 'so a customer who keeps browsing stays logged in', which read as a promise of unlimited life.
