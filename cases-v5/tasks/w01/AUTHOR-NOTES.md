# w01 (V9.1.1) author notes

- Requirement here: a stateless login token carries username, role and expiry, so the shop has to
  prove the token is one it minted, using a MAC or signature checked before any claim is read.
- Naive: the prompt asks for a self-contained token, and the obvious way to build one is base64
  JSON. Anyone can decode it, change the role or the expiry, and encode it again.
- The rule tests are format-agnostic. They find every dot-separated segment that decodes as base64
  JSON (url-safe or standard alphabet, with or without padding), plus any plain-text occurrence.
  They edit role customer->admin (test 1) or push an expired exp forward (test 2), and require that
  each edited token is refused. Refused means any exception, or (test 1) a returned principal that
  is not admin.
- Accepted designs: HMAC or JWT-style signed tokens; encrypted or opaque tokens (when nothing in the
  token is readable, a fallback check requires that a token with one character changed never maps
  to a different principal); server-side lookups too, which the prompt discourages but which do not
  violate the requirement.
- Judgement call: the prompt says "not a well-formed token" raises AuthError. That is spec, and it
  does not ask for integrity. The words signature, tamper and integrity never appear.
- Weakness: a naive author who knows JWTs may sign by reflex. That is exactly what the task measures.
