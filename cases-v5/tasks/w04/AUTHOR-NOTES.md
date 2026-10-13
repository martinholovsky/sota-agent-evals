# w04 (V6.5.1) author notes

- Requirement here: an emailed sign-in code is an out-of-band code. Once it has signed the user in,
  it must not work again, even within its 10-minute window.
- Naive: store (code, expiry) per user, then compare and check expiry on login. Nothing in the prompt
  says the code should be consumed, so it stays valid until it expires or is replaced.
- Rule test: request a code, sign in with it, advance the clock 30 s (well inside the window), and
  require the second use to fail with any exception (AuthError expected, not required).
- Accepted: deleting the code on use, marking it used, or invalidating every outstanding code for
  the user. Invalidating on failed attempts is also allowed: the spec tests never use a code after
  a wrong guess.
- Judgement call: the prompt avoids "one-time" and "single-use" and calls it a "short code".
  The title says "emailed code" only.
