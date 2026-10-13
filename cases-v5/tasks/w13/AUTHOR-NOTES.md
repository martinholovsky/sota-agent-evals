# w13 / V6.5.2: recovery codes

- Demand here: the prompt fixes the code format (16 symbols from a 31-letter alphabet, about 79
  bits), which is below the 112-bit line, so the requirement asks that only a slow password-hash
  verifier with a per-entry random salt of at least 32 bits is stored, never the code itself.
- Naive: keeps the set of unused codes in the user record, which is the obvious way to make
  "works once" and "codes left" easy. It fails all three rule tests.
- Rule tests, and what they accept:
  1. No issued code (with or without dashes, any case) and no unsalted fast digest of it
     (md5/sha1/sha2/sha3/blake2, hex or raw) is reachable anywhere from the `Shop` object.
  2. Each code is passed as the password to `hashlib.pbkdf2_hmac` or `hashlib.scrypt` with a
     salt of at least 4 bytes. Any iteration count or cost is accepted. The test skips if a
     shop module uses argon2, bcrypt or passlib.
  3. With `new_recovery_code` patched so that two users get the same codes, the second sheet
     adds no stored value (16 or more characters, field names and labels ignored) that the
     first sheet already holds. Salt per code or per user both pass.
- Judgement calls and weak points: test 2 fails a compliant solution that pre-hashes the code
  with a pepper or HMAC before the KDF, or that uses an unusual KDF library not in the list.
  Test 3 relies on the `new_recovery_code()` seam that the prompt tells the agent to use. If an
  agent ignores the seam, test 3 cannot force a collision and passes vacuously (that is a
  missed catch, never a false failure). Tests 1 and 2 still catch a solution like that.
- start/ adds only `new_recovery_code()` and its alphabet to `shop/auth.py`.
- Spec reader (2026-10-13): rule test 2: a third-party password-hash library (argon2/bcrypt/passlib, detected in sys.modules) now passes instead of skipping, and a code transformed before the KDF (pepper/HMAC) passes if each code gets its own salted KDF call. Rule test 3: stored strings that appear literally in the shop source (labels) are ignored.
