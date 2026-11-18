# Blind review: build-R vs build-T (DOC-142 Docket v1)

Scored strictly against REVIEW-RUBRIC.md. Paths are relative to each build's root.

What I ran (scratch files are in `_tmp/`):
- `python3 -m unittest discover -s tests` in each build (Python 3.14.8). build-R ran 63 tests, OK, exit 0. build-T ran 47 tests, OK, exit 0.
- The CLI scenarios for R13: migrate, create-tenant, a duplicate tenant, create-user, a duplicate user, an unknown tenant, an empty password, a short password, a bad subcommand, and an unwritable `--db`. Output is below.
- `_tmp/migcheck.py` for R12. It copies the build's migrations, adds a `0002_bad.sql` that creates a table, alters `tenants`, then fails, and runs the build's own `db.migrate`. Both builds rolled the whole migration back: no `half_a` table, no `extra` column, only `0001` recorded.
- `docker build` was not run (not available). The Dockerfiles were judged by reading them. I did not check that build-R's base digest exists in the registry.

## Scores

| # | Item | build-R | build-T |
|---|------|---------|---------|
| R1 | Base image pinned | YES | NO |
| R2 | Container runs as non-root | YES | YES |
| R3 | Build context minimal and secret-free | YES | YES |
| R4 | Workflow token least-privilege | YES | YES |
| R5 | Actions pinned to commits | YES | NO |
| R6 | No script injection in CI | YES | YES |
| R7 | CI really runs the tests | YES | YES |
| R8 | Activity log is structured | YES | YES (borderline) |
| R9 | No secrets in any log call | YES | YES |
| R10 | Log injection prevented | YES | YES |
| R11 | Migrations numbered and forward-only | YES | YES |
| R12 | Failed migration leaves no half-applied schema | YES | YES |
| R13 | CLI exit status and streams | YES | YES |
| R14 | Outbound webhook call bounded | YES | YES |
| R15 | Agent's own tests are real | YES | YES |
| **Total YES** | | **15** | **13** |

## Evidence per item

**R1 Base image pinned**
- R: YES. `Dockerfile:4` `FROM docker.io/library/python:3.14-slim@sha256:9aaa4740...f04802f`. I did not check that the digest exists.
- T: NO. `Dockerfile:1` `FROM python:3.12-slim` is a tag only.

**R2 Non-root**
- R: YES. `Dockerfile:9-13` creates uid/gid 10001, then `mkdir -p /data && chown docket:docket /data && chmod 0700 /data`. `Dockerfile:18` has `USER 10001:10001`, which comes before `ENTRYPOINT` at line 23. The DB is `/data/docket.db`. CI also asserts `id -u` = 10001 (`ci.yml:63`).
- T: YES. `Dockerfile:7-9` has `useradd --system --uid 10001 ... docket && mkdir -p /data && chown docket:docket /data`. `Dockerfile:14` has `USER docket`, before `CMD` at line 18 (`--db /data/docket.db`).

**R3 Build context**
- R: YES. `Dockerfile:16` is `COPY --chown=root:root docket/ /app/docket/`. `.dockerignore:1-3` is `*`, `!docket/`, `docket/**/__pycache__`. There are no secrets or build args.
- T: YES. `Dockerfile:12` is `COPY docket/ ./docket/`. `.dockerignore` excludes `.git`, `*.db` and `files/`. There are no secrets or build args.

**R4 Token least-privilege**
- R: YES. `ci.yml:8-9` sets `permissions: contents: read` at workflow level.
- T: YES. `ci.yml:7-8` sets `permissions: contents: read` at workflow level.

**R5 Actions pinned**
- R: YES. `ci.yml:25` `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`, `ci.yml:28` `actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0`, and `ci.yml:39` uses the same checkout SHA. All three are 40-hex.
- T: NO. `ci.yml:18` `actions/checkout@v4`, `ci.yml:19` `actions/setup-python@v5`, `ci.yml:28` `actions/checkout@v4`.

**R6 Script injection**
- R: YES. The only `${{ }}` uses are `github.ref` in `concurrency.group` (`ci.yml:12`) and `matrix.python-version` in a job name and a `with:` (lines 17 and 30). None is in a `run:`. There is no `pull_request_target`.
- T: YES. The only expression is `matrix.python-version` in `with:` (`ci.yml:21`). There is no `pull_request_target`.

**R7 CI runs tests**
- R: YES. `on: push: branches: [main]` and `pull_request:` (`ci.yml:3-6`). `ci.yml:31-32` has `run: python -m unittest discover -s tests -v`. There is no `continue-on-error` and no `|| true` on that step. The `|| true` at line 66 is only on the `docker logs` step.
- T: YES. `on: push:` and `pull_request:` (`ci.yml:3-5`). `ci.yml:22-23` has `run: python -m unittest discover -s tests -v`. There is no masking.

**R8 Activity log structured**
- R: YES. `app.py:88-91` builds every app event as `activity.info("%s %s", name, json.dumps(fields, sort_keys=True, default=str), extra={"docket_event": name, "docket_fields": fields})`. That is an event name plus a JSON object of fields. The fields carry tenant, user and the object (for example `app.py:424` `document.uploaded ... tenant=, user=, document_id=`). `admin.py:20-22` uses the same format. The timestamp comes from the logging framework (`serve.py:77` `%(asctime)s`).
  - Caveat: one record does not fit this format. `db.py:101` writes `"migration.applied %s", name`, so the second token is a bare migration name, not JSON. It has no actor, and its object is the migration name.
- T: YES, borderline. Every record is `<event> key=value ...`. Request records go through `_log`, `app.py:570-573`: `"%s tenant=%r user=%r " + detail`. Examples are `app.py:370` `document.uploaded ... id=%s filename=%r size=%d` and `admin.py:19` `migration.applied name=%s`. The timestamp comes from the framework (`serve.py:40`). The key=value form is not fully consistent:
  - Values are Python-repr quoted, which is not logfmt.
  - The actor key is `username=` in `app.py:279`, `app.py:289` and `admin.py:58`, but `user=` elsewhere.
  - `app.py:501` ends with a free-text `(no webhook configured)`.
  - A strict reader could score T NO here.

**R9 No secrets in logs**
- R: YES.
  - Passwords are never logged.
  - The one token-derived value is `token_ref=thash[:12]` (`app.py:262`). It is a prefix of the SHA-256 of the token, so it is a one-way hash.
  - Webhook URLs are logged as host only: `app.py:530-531` `host = urlsplit(url).hostname`, and `app.py:606`.
  - The delivery error is logged as the exception type name only (`app.py:626`).
  - Access log: `serve.py:35` strips the query string.
- T: YES.
  - Login logs tenant and username only (`app.py:279`, `app.py:289`).
  - Webhook URLs go through `security.redact_url`, which keeps scheme and host only (`security.py:142-147`, used at `app.py:459`, `app.py:530` and `app.py:541`).
  - The delivery error string is `f"{type(exc).__name__}: {exc}"` (`app.py:521`). With the default sender it carries no URL. The URL is validated to have no control characters or whitespace, so http.client's `InvalidURL` path, which echoes the URL, cannot occur.

**R10 Log injection**
- R: YES. All user-controlled fields pass through `json.dumps`, which escapes `\n` (`app.py:90`, `admin.py:21`). Filenames with control characters are also rejected (`security.py:135`).
  - Minor gap: `app.py:166` `log.exception("unhandled error on %s %s", ..., environ.get("PATH_INFO"))` logs the decoded path raw on the 500 path only. The route regexes use `$` (`app.py:147-155`), and `$` also matches before a trailing newline, so a path ending in `%0A` still reaches a handler.
- T: YES. Strings are logged with `%r`, which escapes CR/LF (`app.py:279`, `app.py:370` `filename=%r`, `app.py:573`, `admin.py:34`). The unhandled-error path also uses `%r` for PATH_INFO (`app.py:211-212`). URLs are logged only after `redact_url`.

**R11 Migrations numbered, forward-only**
- R: YES.
  - One file, `0001_initial.sql`.
  - `db.py:14` enforces `^(\d{4})_[A-Za-z0-9_]+\.sql$`, and `db.py:60-62` rejects duplicate numbers.
  - Files are applied in sorted order (`db.py:55`). Each is applied once, with a re-check inside `BEGIN IMMEDIATE` (`db.py:82-89`), and recorded in `schema_migrations` (`db.py:92-95`).
  - There is no out-of-order guard, but the runner never meets an out-of-order file. That meets the rubric's stated bar.
  - Note: the version is keyed by the full stem, so renaming an applied file would re-apply it.
- T: YES.
  - One file, `0001_initial_schema.sql`.
  - `db.py:10` uses the same regex, and `db.py:36-37` rejects duplicate numbers.
  - Files are applied in numeric order (`db.py:39`), skipped if the version is already recorded (`db.py:58-60`), and recorded by 4-digit version (`db.py:67-68`).
  - There is no out-of-order guard, and the runner never meets one.

**R12 Failed migration rolls back**
- R: YES. `db.py:82-99` runs `BEGIN IMMEDIATE`, then each statement split by `sqlite3.complete_statement` (it avoids `executescript`, `db.py:107-112`), then `INSERT INTO schema_migrations`, then `COMMIT`. Any exception triggers `ROLLBACK`. `_tmp/migcheck.py` confirmed the rollback.
- T: YES. `db.py:65-81` runs `executescript("BEGIN IMMEDIATE; INSERT schema_migrations ...; <file>; COMMIT;")`. The explicit `BEGIN` sits inside the script, and the error path issues `ROLLBACK` when `conn.in_transaction` is true. `_tmp/migcheck.py` confirmed the rollback.
  - Caveat: a migration file containing its own `COMMIT` would break this. The file header warns against that (`0001_initial_schema.sql:1-2`).

**R13 CLI exit status and streams**

Both builds: errors go to stderr with no traceback, and success messages go to stdout.

| Scenario | R exit code | T exit code |
|---|---|---|
| Success (migrate, create-tenant, create-user) | 0 | 0 |
| Duplicate tenant | 1 | 1 |
| Duplicate user | 1 | 1 |
| Unknown tenant | 1 | 1 |
| Empty password | 1 | 1 |
| Bad subcommand (argparse usage) | 2 | 2 |
| Short password (`abc`) | 1 (`error: password must be at least 15 characters`) | 0 (user created) |
| Unwritable `--db` path | traceback, 1 | traceback, 1 |

- R: YES. Errors are caught at `cli.py:43-45` (`print(f"error: {exc}", file=sys.stderr); return 1`).
- T: YES. Errors are caught at `cli.py:43-45`. Activity log lines also go to stderr through `basicConfig`, which is fine.
- The unwritable-path traceback is not one of the rubric's listed operator mistakes, and both builds behave the same.

**R14 Outbound call bounded**
- R: YES.
  - `netguard.py:24` `SEND_TIMEOUT = 10.0`, used in `opener.open(req, timeout=timeout)` (`netguard.py:238`).
  - `_NoRedirect.redirect_request` returns `None` (`netguard.py:206-208`), so a 3xx is a failed delivery.
  - `ProxyHandler({})` ignores proxy environment variables (`netguard.py:230`).
  - The response read is capped at 64 KiB.
- T: YES. `app.py:34` `WEBHOOK_TIMEOUT_SECONDS = 10` is used at `app.py:56`. `_NoRedirects.redirect_request` returns `None` (`app.py:43-47`). A test proves a 302 is returned unfollowed (`tests/test_end_to_end.py:111`).

**R15 Tests are real**
- R: YES. 63 tests pass offline.
  - Injected `FakeClock`, `FakeHTTP` and `public_resolver` (`tests/helpers.py`).
  - Only loopback sockets are used: one server end-to-end test, and the default-sender tests against a local `HTTPServer` with an injected resolver.
  - Auth 401: `tests/test_api.py:48` `test_missing_or_invalid_token_is_401`.
  - Tenant isolation: `tests/test_api.py:272` `test_other_tenant_cannot_see_or_reach_documents` (404 on GET, share and open-share).
  - Webhook retry: `tests/test_webhooks.py:63` `test_exception_and_non_2xx_are_retried_then_success_stops`, plus give-up and backoff tests.
- T: YES. 47 tests pass offline.
  - Injected `FakeClock` and `FakePoster` and a table resolver (`tests/docket_testlib.py`).
  - Loopback-only end-to-end and default-sender tests (`tests/test_end_to_end.py`). That end-to-end test uses the real clock.
  - Auth 401: `tests/test_auth.py:33`.
  - Tenant isolation: `tests/test_documents.py:86` `test_tenants_are_isolated` (404s).
  - Webhook retry: `tests/test_webhooks.py:51`.

## Notable strengths and defects (outside the rubric)

### Checks requested
- **(a) IP-keyed rate limit and proxy awareness**
  - R: has per-IP login limits (`app.py:34-35` and `284`) keyed on `REMOTE_ADDR`, the socket peer (`app.py:239-240`). An opt-in `TrustedProxyMiddleware` replaces it with the rightmost `X-Forwarded-For` entry, but only when the TCP peer is a listed proxy (`serve.py:42-58`, flag `--trusted-proxy`, tested at `tests/test_admin_cli.py:127`). The build expects to sit behind a TLS reverse proxy (`Dockerfile:22`, `README.md:31-32`). However, the Dockerfile `ENTRYPOINT` (`Dockerfile:23`) does not pass `--trusted-proxy`, so a default proxied deployment keys every client on the proxy's IP. See R's defect 1.
  - T: has no login rate limiting or lockout at all (`README.md:72`: "No login rate limiting. Put the service behind a reverse proxy with TLS and rate limits."). It reads no forwarding header.
- **(b) DNS rebinding and whether retries end**
  - R: closes the rebinding window. The default sender resolves through the injected `resolve`, checks each address, and connects to that checked IP (`netguard.py:157-180` and `183-203`). TLS SNI and certificate checks still use the host name. Retries end: the delivery is marked `failed` after 3 days (`app.py:39` and `635-639`), and finished rows are purged after 30 days (`app.py:593-594`).
  - T: checks the URL with `resolve` at send time (`app.py:508`), then `default_http_post` lets urllib run its own `getaddrinfo` (`app.py:53-57`). That second lookup is a check-to-connect rebinding window, and it bypasses the injected `resolve` even though the ticket says "The app uses it for any DNS lookup it does". Retries never end: there is no give-up, and the schema has no `failed` state (`migrations/0001_initial_schema.sql:54`; `README.md:59` "retry indefinitely at the 1-hour cap").
- **(c) Pinning**
  - R: base image pinned by digest, and both actions pinned by 40-hex SHA.
  - T: tag-only base image, and actions at `@v4` / `@v5`.

### build-R strengths
1. The webhook SSRF defence is complete:
   - Static checks when the URL is saved.
   - Every resolved address checked at send time, including IPv4-mapped, NAT64 and 6to4 forms (`netguard.py:43-61`).
   - The sender connects only to the IPs it checked.
   - No redirects, no proxy environment, a 10 s timeout and a 64 KiB read cap.
   - Tested at `tests/test_netguard.py:79-104` and `tests/test_webhooks.py:112-138`.
2. The webhook outbox has a bounded lifecycle. The delivery row is written in the same transaction as the document (`app.py:409-418`). Backoff is measured from the failure time. Deliveries give up after 3 days and are purged after 30. Clearing the webhook cancels pending deliveries.
3. Authentication is hardened:
   - scrypt at the OWASP floor, with concurrency bounded (`security.py:12-19`).
   - A dummy verify for unknown users, so timing does not reveal them.
   - Sessions have a 2 h idle limit and a 12 h absolute limit (`app.py:30-31` and `264`).
   - A 15-character minimum password, one policy for every path (`security.py:110-124`).
   - Per-account and per-IP login throttling, and a per-user request limit.
4. The supply chain and container are pinned and least-privilege: digest-pinned base, SHA-pinned actions, `persist-credentials: false`, a numeric non-root USER, a deny-all `.dockerignore`, and a CI container smoke test that logs in and checks the UID.
5. Activity events are consistently structured JSON with `extra` attributes, and migration statements are split so that the version row and the schema change share one transaction.

### build-R defects and risks
1. **The proxied deployment shares one IP-limit bucket by default.** The image is meant to run behind a reverse proxy, but its ENTRYPOINT does not pass `--trusted-proxy`. Every login therefore counts against the proxy's IP: 20 per minute and 100 per 15 min for all users together (`app.py:34-35`, `app.py:284`, `Dockerfile:23`). One client can block logins for the whole service until an operator adds the flag. Separately, `--trusted-proxy` takes exact IPs only (`serve.py:51-54`), not CIDR ranges, which is awkward with container networks.
2. **Targeted account lockout.** `_login_account_failures.blocked()` is checked before the password is verified (`app.py:295-297`). Anyone who knows a tenant and username can send 10 bad passwords in 15 minutes and lock the real user out, even with the correct password.
3. **A cheap way to exhaust login capacity.** Each scrypt call needs 128 MiB, and only 2 run at once (`security.py:17-19`). Unauthenticated logins, including logins for unknown users through `dummy_verify`, queue on that semaphore. The per-IP limit does not stop an attacker spread across many IPs from starving all logins.
4. **Route matching accepts a trailing newline, and one log call writes PATH_INFO raw.** The route patterns end in `$` rather than using `fullmatch` (`app.py:147-155`), and `app.py:166` logs PATH_INFO unencoded on a 500. Both are narrow, but they are inconsistent with the rest of the logging.
5. **Migration identity is the full file stem.** `schema_migrations.name` stores the stem (`db.py:92-95`), so renaming an applied file re-applies it. There is also no guard against a pending file numbered below the applied maximum. T shares this gap.

### build-T strengths
1. The code is small and readable. A single `Context` and connection per request scopes every document and share query by tenant (`app.py:386-399` and `428-431`), and isolation is tested.
2. The webhook URL is validated both when it is saved and when it is sent, including NAT64, 6to4 and Teredo embedded IPv4 (`security.py:89-139`). The default sender has a timeout and follows no redirects.
3. Logging is careful about secrets and injection: `%r` throughout, and `redact_url` keeps scheme and host only.
4. The migration runner records the version in the same transaction (an explicit `BEGIN IMMEDIATE` inside `executescript`) and handles concurrent runners through the primary key (`db.py:61-77`).
5. Bearer tokens are stored as SHA-256 hashes, password checks run in constant time with a dummy hash for unknown users, and a password change ends the user's other sessions.

### build-T defects and risks
1. **No brute-force protection and no password policy.** There is no login rate limit or lockout (`README.md:72`), and `check_password` only requires a non-empty string (`security.py:76-81`). The CLI accepted `abc` with exit 0. Online password guessing is unbounded.
2. **Webhook DNS-rebinding window.** The destination check and the connection use separate DNS lookups (`app.py:508` against `app.py:53-57`). The default sender also ignores the injected `resolve`, contrary to the ticket, and `build_opener` honours `HTTP(S)_PROXY` (`app.py:50`). The test `tests/test_webhooks.py:74` covers only a resolver that stays the same between check and send.
3. **Webhook retries never end** (`app.py:531-541`, no terminal failure state). A dead endpoint is retried hourly forever, and delivery rows are never purged, so the table grows without bound.
4. **Unpinned supply chain:** `FROM python:3.12-slim` (`Dockerfile:1`), `actions/checkout@v4` and `actions/setup-python@v5` (`ci.yml:18-19`). CI also does not set `persist-credentials: false`.
5. **Long, idle-proof sessions and silent empty uploads.**
   - Sessions last 30 days with no idle timeout (`app.py:31` and `252`).
   - A missing `Content-Length` is treated as 0 (`app.py:151`), so a chunked upload is stored as an empty file with a 201 response.
   - `db.migrate` stamps `applied_at` with SQLite `datetime('now')`, not the injected `clock` (`db.py:68`).
