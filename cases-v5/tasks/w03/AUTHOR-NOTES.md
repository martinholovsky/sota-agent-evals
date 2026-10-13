# w03 (V16.3.1) author notes

- Requirement here: API keys are a second way to authenticate. Every use of one, successful or failed,
  must leave a record, and that record should say which kind of authentication was used.
- Naive: the prompt asks for an event when a key is created (a state change) but says nothing
  about events on authentication. Checking a key changes no state, so a convention-following
  implementation emits nothing and API-key logins are invisible.
- Rule tests (method-agnostic): a successful key use must emit at least one event that names the user
  and differs (ignoring timestamp and username) from what a password login emits. A failed key use
  must emit at least one event that differs from both a success and a failed password login. Any
  event type, field name or method label is accepted ("api_key_login_ok", login_ok+method=...,
  "auth" with method/result fields, and so on).
- Judgement call: ASVS frames the method metadata as a "should". The tests still require success and
  failure to be told apart from password logins. Otherwise a reused login_ok/login_failed
  without a method would hide which credential was used, which is the core of logging a new
  authentication path. A grader who reads "should" strictly may call test 1's method clause strict.
- Weakness: a naive author who copies `Users.login` emits login_ok/login_failed by imitation. That
  version would still fail both tests, because nothing records the method.
- Spec reader (2026-10-13): rule tests widened: recording the method is a 'should' in the requirement, so test 1 now needs only an event naming the user on success, and test 2 only a failure event that differs from a success event (a reused login_ok/login_failed passes). The naive still fails both: it emits nothing.
