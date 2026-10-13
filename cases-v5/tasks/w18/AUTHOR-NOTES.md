# w18 (V6.6.3)

- Requirement here: the emailed 6-digit password-reset code must not be open to unlimited
  guessing; wrong attempts have to be limited.
- The prompt fixes the code at 6 digits, so the "longer code" alternative the requirement
  mentions is not available; limiting attempts is the only compliant route.
- Naive checks code, expiry and single use, but counts nothing, so an attacker can try codes
  until one matches within the 15-minute window.
- Rule test: 100 wrong codes at one clock instant, then the real code; passes if afterwards the
  new password does not log in. Accepts voiding the code, locking the code or account, throttling
  with any exception, or any threshold up to 100.
- Judgement call: the prompt says one mistyped code must not block the right one (a usability
  spec); this rules out only a limit of 1 and is tested only by one wrong-then-right attempt.
- Not tested: resetting the counter by requesting a new code (a real bypass, but contestable
  as a requirement violation, so left out to keep the test fair).
