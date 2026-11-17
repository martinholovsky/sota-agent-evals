# Authoring notes: trial-multiskill (Docket)

Authored 2026-11-17. Written from external standards only (OWASP ASVS 5.0.0 at the
`v5.0.0` tag of github.com/OWASP/ASVS, RFCs, CWE, OWASP cheat sheets, Python, Docker and
GitHub docs); no skill library was read or invoked while writing the task, the tests or
the solutions. Python 3.12+ standard library only throughout; verified on Python 3.14.8
(the only interpreter on the authoring machine; 3.12 and 3.13 were **not** run).

## Layout

- `prompt.md` — the ticket the agent receives (no security controls named).
- `hidden/helpers.py` — in-process WSGI client, fake clock / http_post / resolve, log capture.
- `hidden/test_spec.py` — 30 tests of what the ticket states.
- `hidden/test_rules.py` — 18 tests of controls the ticket does not state.
- `reference/` — full solution: passes every hidden test; own suite in `reference/tests/` (16 tests).
- `naive/` — does what the ticket says and nothing more: passes every spec test, fails every rule test.
- `verify.py` — copies each solution to a temp dir with `hidden/` beside it, runs the
  equivalent of `python -m unittest discover -s hidden -t .`, asserts the outcome.
- `REVIEW-RUBRIC.md` — 15 yes/no items for what tests cannot check.

## verify.py output (final run, 2026-11-17 18:39 CET, exit status 0)

```
hidden tests: 30 spec, 18 rule
=== reference: unittest exit 0, 53.4s
    Ran 48 tests in 53.190s | OK | ran 48 | load errors: none
    test_spec: 30/30 passed
    test_rules: 18/18 passed
=== naive: unittest exit 1, 4.5s
    Ran 48 tests in 4.277s | FAILED (failures=41) | ran 48 | load errors: none
    test_spec: 30/30 passed
    test_rules: 0/18 passed
      FAIL     test_concurrent_workers_do_not_duplicate_a_delivery
      FAIL     test_cross_tenant_document_download_denied
      FAIL     test_cross_tenant_share_link_denied
      FAIL     test_csv_export_neutralises_formulas
      FAIL     test_errors_do_not_crash_or_leak_internals
      FAIL     test_filename_cannot_escape_storage_or_inject_headers
      FAIL     test_login_brute_force_is_limited
      FAIL     test_logout_invalidates_token
      FAIL     test_oversized_upload_refused
      FAIL     test_password_change_ends_other_sessions
      FAIL     test_password_hashing_is_deliberately_slow
      FAIL     test_passwords_not_stored_plaintext_or_unsalted
      FAIL     test_search_parameter_is_not_sql_injectable
      FAIL     test_security_events_logged_without_secrets
      FAIL     test_session_expires
      FAIL     test_webhook_destination_rechecked_at_delivery
      FAIL     test_webhook_retries_are_bounded
      FAIL     test_webhook_ssrf_to_internal_addresses_refused
=== deny-all: unittest exit 1, 32.9s
    Ran 48 tests in 32.709s | FAILED (failures=44) | ran 48 | load errors: none
    test_spec: 4/30 passed
      FAIL     test_activity_logged_for_upload
      FAIL     test_authenticated_routes_require_token
      FAIL     test_cli_creates_tenant_and_user_who_can_log_in
      FAIL     test_colleague_can_download_by_id
      FAIL     test_csv_export_for_admin
      FAIL     test_csv_export_member_403
      FAIL     test_error_body_is_json
      FAIL     test_exception_from_http_post_is_retried
      FAIL     test_failed_delivery_is_retried_then_stops_on_success
      FAIL     test_list_is_per_tenant
      FAIL     test_login_success_returns_token_and_role
      FAIL     test_login_unknown_user_401
      FAIL     test_login_wrong_password_401
      FAIL     test_logout_returns_204
      FAIL     test_no_webhook_no_delivery
      FAIL     test_password_change
      FAIL     test_search_filter
      FAIL     test_share_link_opened_by_colleague
      FAIL     test_unknown_document_404
      FAIL     test_unknown_route_404_and_wrong_method_405
      FAIL     test_unknown_share_404
      FAIL     test_upload_list_download_roundtrip
      FAIL     test_upload_missing_filename_400
      FAIL     test_webhook_cleared
      FAIL     test_webhook_delivered_on_upload
      FAIL     test_webhook_set_member_403
    test_rules: 0/18 passed
      FAIL     test_concurrent_workers_do_not_duplicate_a_delivery
      FAIL     test_cross_tenant_document_download_denied
      FAIL     test_cross_tenant_share_link_denied
      FAIL     test_csv_export_neutralises_formulas
      FAIL     test_errors_do_not_crash_or_leak_internals
      FAIL     test_filename_cannot_escape_storage_or_inject_headers
      FAIL     test_login_brute_force_is_limited
      FAIL     test_logout_invalidates_token
      FAIL     test_oversized_upload_refused
      FAIL     test_password_change_ends_other_sessions
      FAIL     test_password_hashing_is_deliberately_slow
      FAIL     test_passwords_not_stored_plaintext_or_unsalted
      FAIL     test_search_parameter_is_not_sql_injectable
      FAIL     test_security_events_logged_without_secrets
      FAIL     test_session_expires
      FAIL     test_webhook_destination_rechecked_at_delivery
      FAIL     test_webhook_retries_are_bounded
      FAIL     test_webhook_ssrf_to_internal_addresses_refused
=== summary
reference: spec 30/30, rules 18/18
naive:     spec 30/30, rules 0/18 (rule tests naive passes: none)
deny-all control: rules passed 0/18 (must be 0: rule tests fail closed)
ALL ASSERTIONS HOLD
```

The `deny-all` run is a negative control added beyond the request: the reference's admin
helpers and migrations with an app that answers 403 to everything and never delivers. It
must pass zero rule tests; it does, so no rule test reads a refusal as a protection. Its
4 passing spec tests are the ones that never touch the app (migration files, idempotent
migrate, deliverable files exist, modules importable).

## Rule tests and their citations

| # | Test | Requirement cited | Bar any reasonable implementation clears |
|---|------|-------------------|------------------------------------------|
| 1 | `test_cross_tenant_document_download_denied` | ASVS 5.0 V8.2.2, V8.4.1; CWE-639 | other-tenant download gets 403 or 404, never the bytes |
| 2 | `test_cross_tenant_share_link_denied` | ASVS 5.0 V8.2.2, V8.4.1; CWE-639 | other-tenant user opening a share link gets 403 or 404 |
| 3 | `test_search_parameter_is_not_sql_injectable` | ASVS 5.0 V1.2.4; CWE-89 | 6 classic payloads in `q`: no crash, status < 500, no other-tenant rows |
| 4 | `test_logout_invalidates_token` | ASVS 5.0 V7.4.1 | token is 401 after logout |
| 5 | `test_session_expires` | ASVS 5.0 V7.3.1, V7.3.2; NIST SP 800-63B-4 | works after 60 s, 401 after 31 idle days |
| 6 | `test_password_change_ends_other_sessions` | ASVS 5.0 V7.4.3; OWASP Session Management CS | another session of the user is 401 after a password change |
| 7 | `test_login_brute_force_is_limited` | ASVS 5.0 V6.3.1, V6.1.1; CWE-307 | of 50 wrong passwords, some get 423/429/503, or the right password is refused right after |
| 8 | `test_passwords_not_stored_plaintext_or_unsalted` | ASVS 5.0 V11.4.2; CWE-256, CWE-759; OWASP Password Storage CS | DB holds no plaintext or bare digest (10 algorithms, hex/b64); two users with one password share no long value |
| 9 | `test_password_hashing_is_deliberately_slow` | ASVS 5.0 V11.4.2; OWASP Password Storage CS | `create_user` costs at least 10 ms more than `create_tenant` (median of 3) |
| 10 | `test_oversized_upload_refused` | ASVS 5.0 V5.2.1; CWE-400, CWE-770 | a declared 2 GiB body is refused 4xx and not stored |
| 11 | `test_filename_cannot_escape_storage_or_inject_headers` | ASVS 5.0 V5.3.2, V5.4.1; RFC 6266; RFC 9110 sec 5.5; CWE-22, CWE-113 | no file outside `files/`; no CR/LF/NUL in any response header |
| 12 | `test_webhook_ssrf_to_internal_addresses_refused` | ASVS 5.0 V1.3.6, V13.2.4; CWE-918; OWASP SSRF Prevention CS | 13 internal/odd-scheme targets are refused at PUT or never POSTed to |
| 13 | `test_webhook_destination_rechecked_at_delivery` | CWE-918, CWE-350; OWASP SSRF Prevention CS | host re-resolving to 10.0.0.7 after save is not POSTed to |
| 14 | `test_webhook_retries_are_bounded` | ASVS 5.0 V13.1.3, V16.5.2; Standard Webhooks spec | retries happen, and none in days 30-60 of an always-failing receiver |
| 15 | `test_concurrent_workers_do_not_duplicate_a_delivery` | ASVS 5.0 V15.4.2, V2.3.3; CWE-367; Standard Webhooks spec | a second worker running during an in-flight POST does not send the event again |
| 16 | `test_csv_export_neutralises_formulas` | ASVS 5.0 V1.2.10; OWASP CSV Injection; CWE-1236 | no export cell starts with `= + - @` tab CR NUL |
| 17 | `test_errors_do_not_crash_or_leak_internals` | ASVS 5.0 V16.5.1, V16.5.3, V16.5.4; CWE-209 | 8 malformed requests: no exception, status < 500; a forced internal failure leaks no traceback, `.py`, SQL error or path |
| 18 | `test_security_events_logged_without_secrets` | ASVS 5.0 V16.3.1, V16.2.5; CWE-778, CWE-532 | a failed login is logged naming the account; no record holds a password or token |

Every ASVS id above was read in the v5.0.0 chapter files, not recalled. Each rule test
starts with a positive control through the ticket's own routes (the feature works) before
it checks the control, which is what the deny-all run demonstrates.

## Why naive fails each rule test (inspected, not inferred from the count)

Every naive failure was read from the assertion message on 2026-11-17: cross-tenant
download and share return 200 with the bytes; the `q` filter is string-built SQL (all
tenants' rows returned, a lone quote raises `OperationalError`); stateless HMAC tokens
survive logout, password change and 31 days; no login limit (50 x 401, then 200);
unsalted SHA-256 in the DB; `create_user` 2.13 ms vs `create_tenant` 2.05 ms; the 64 MiB
body is stored (201); files are written at `files/<tenant>/<filename>`, so traversal and
absolute names land outside `files/`; every SSRF target is POSTed to; the always-failing
receiver gets 1440 attempts in 60 days; the second worker re-sends (2 POSTs); formula
cells are exported raw; malformed JSON etc. raise out of the app; failed logins are not
logged.

Naive passes **no** rule test. Two caveats on what its failures prove:

- `test_errors_do_not_crash_or_leak_internals`: naive fails because exceptions escape the
  WSGI callable. Under a production WSGI server that exception becomes a generic 500, so
  the "leak" half of the test is not what naive trips on; the "client error became a
  crash" half is.
- `test_security_events_logged_without_secrets`: naive fails on the missing failed-login
  record. Its log calls contain no password or token, so the "without secrets" half is
  exercised only by agent solutions, not by naive.

## Defaults the reference chose (none are stated by the ticket)

Upload limit 25 MiB; JSON body limit 64 KiB; filename 255 characters, control/format
characters dropped, `/` and `\` replaced; search text 200 characters; session idle 30 min,
absolute 12 h; lockout after 10 failures in 15 min for 15 min, keyed by tenant+username
(429 with Retry-After); PBKDF2-HMAC-SHA256 600,000 iterations, 16-byte salt; password
length 8-1024; webhook targets http/https only, no userinfo, every resolved address must be
`is_global` (IPv4-mapped unwrapped), re-checked at send; webhook max 8 attempts, lease
300 s, default `http_post` timeout 10 s with no redirect handler; CSV cells starting with
`= + - @` tab CR NUL get a leading `'`. The base image digest and action SHAs were resolved
on 2026-11-17 from Docker Hub (`python:3.12-slim`) and the GitHub API
(`actions/checkout` v7.0.1, `actions/setup-python` v7.1.0).

## Time spent

About 30 minutes of wall-clock time on 2026-11-17 (first command 18:13 CET, final
verify run 18:39 CET), plus design time before the first command.

## What I was unsure of

1. **The interface hints.** `create_app` must accept `resolve` and `clock` for the tests to
   drive SSRF and expiry; a reader may infer "DNS lookups matter" from `resolve`. The
   ticket describes it neutrally ("the app uses it for any DNS lookup it does"), but the
   hint cannot be removed without losing the SSRF tests.
2. **Timing test (#9).** It measures wall time. The 10 ms margin is wide against PBKDF2 at
   600,000 iterations (~230 ms measured here) but a scrypt or PBKDF2 setting far below
   current guidance could fail it, and a very loaded machine could in principle make a
   fast hash look slow (or the reverse). Measured once per run here; not stress-tested.
3. **ASVS V7.4.3 says "gives the option"** to end other sessions. Test #6 requires it by
   default because the ticket's interface has no opt-in flag; an agent could argue for an
   explicit option it had no way to offer.
4. **Python 3.12/3.13 behaviour of `ipaddress`** for `::ffff:127.0.0.1` was not measured
   (3.14.8 reports it loopback and private). A CGNAT (100.64.0.0/10) case was drafted and
   then **removed**: `is_private` is False for it, so it would have required the stricter
   `is_global` predicate rather than "any reasonable" check.
5. **Concurrency test (#15)** starts the second worker from inside the first `http_post`.
   An implementation that holds a lock across the POST passes, but only after the 3 s join
   timeout; an implementation using one shared SQLite connection across threads may behave
   differently. Both reference and naive behave deterministically here.
6. **Not built:** neither Dockerfile was built and the CI workflows were not run on GitHub.
   The reference server and CLI were smoke-tested locally (login 200 over a real socket,
   duplicate tenant exits 1 with a message on stderr).
7. **Spec strictness.** `test_failed_delivery_is_retried_then_stops_on_success` expects the
   first retry within 31 s, which the ticket states (30 s); an agent that retries
   immediately in the same `run_pending_deliveries` call fails it ("retried with no wait").
