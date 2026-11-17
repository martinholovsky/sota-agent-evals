# Docket blind review: build-P vs build-Q

Scored strictly by REVIEW-RUBRIC.md. Only files under `blind-review/` were read. No file in either
build was edited.

## Commands run

- `python3 -m unittest discover -s tests` from each build root (Python 3.14.8, `PYTHONDONTWRITEBYTECODE=1`):
  build-P `Ran 55 tests ... OK`, exit 0. build-Q `Ran 96 tests ... OK`, exit 0.
- Ran each CLI (`python3 -m docket.cli`) against a throwaway DB in a `mktemp -d` directory (removed
  afterwards) for: migrate, create-tenant, duplicate tenant, unknown tenant, create-user, duplicate user,
  empty password, short password, unknown subcommand, `--db /nonexistent/dir/x.db`, empty tenant name.
  Exit status, stdout and stderr were captured separately.
- build-P migration atomicity: an inline script pointed `db.MIGRATIONS_DIR` at a temp dir holding
  `0001_a.sql` (valid) and `0002_b.sql` (`CREATE TABLE b (x); THIS IS NOT SQL;`). Result:
  `OperationalError` raised, tables `['a', 'schema_migrations']`, recorded `['0001_a.sql']`. No `b`, so the
  rollback works. build-Q has the same check as its own passing test
  (`tests/test_admin_and_migrations.py:36-48`).
- Lengths of the action pins: every build-Q `uses:` ref is 40 characters. Every build-P ref is `v4` or `v5`.
- `docker build` was not available, so both Dockerfiles were judged by reading them.

## Scores

| Item | build-P | build-Q |
|---|---|---|
| R1 Base image pinned | NO | YES |
| R2 Non-root container | YES | YES |
| R3 Minimal, secret-free context | YES | YES |
| R4 Least-privilege workflow token | YES | YES |
| R5 Actions pinned to commit SHA | NO | YES |
| R6 No script injection in CI | YES | YES |
| R7 CI really runs the tests | YES | YES |
| R8 Structured activity log | YES | YES |
| R9 No secrets in any log call | YES | YES |
| R10 Log injection prevented | YES | YES |
| R11 Migrations numbered, forward-only | YES | YES |
| R12 Failed migration leaves nothing half-applied | YES | YES |
| R13 CLI exit status and streams | YES (borderline) | NO (borderline) |
| R14 Outbound webhook call bounded | YES | YES |
| R15 Own tests are real | YES | YES |
| **YES count** | **13 / 15** | **14 / 15** |

Two scores are borderline, and both are R13. Under the opposite reading of each, the counts become P 12
and Q 15. The reasons are under R13 below.

## Evidence per item

### R1 Base image pinned
- **P: NO.** `Dockerfile:1` `FROM python:3.12-slim` names a tag only, with no digest.
- **Q: YES.** Both stages are pinned by digest:
  - `Dockerfile:8` `FROM docker.io/library/python:3.14-slim@sha256:9aaa4740...802f AS prep`
  - `Dockerfile:11` `FROM gcr.io/distroless/python3-debian13:nonroot@sha256:6c4cb3bf...ae71`
  - `.github/dependabot.yml:7` also proposes docker digest updates.

### R2 Container runs as non-root
- **P: YES.**
  - `Dockerfile:7-9` runs `useradd --system --uid 10001 ... docket && mkdir -p /data && chown docket:docket /data`.
  - `Dockerfile:14` sets `USER docket`, before `CMD` at `:18`.
  - The DB lives at `/data/docket.db` (`:18`), which that user can write.
- **Q: YES.**
  - `Dockerfile:9` runs `install -d -o 65532 -g 65532 -m 0700 /data`.
  - `Dockerfile:16` has `COPY --from=prep --chown=65532:65532 /data /data`.
  - `Dockerfile:21` sets `USER 65532:65532`, before `ENTRYPOINT` at `:28`. The code stays root-owned (`:17-18`).

### R3 Build context is minimal and secret-free
- **P: YES.**
  - `Dockerfile:12` copies only the package: `COPY docket/ ./docket/`.
  - `.dockerignore:1-7` excludes `.git`, `.github`, `tests`, `*.db`, `*.db-*` and `files/`.
  - The Dockerfile contains no credentials and no build args.
- **Q: YES.**
  - `Dockerfile:18` copies only the package: `COPY docket/ /app/docket/`.
  - `.dockerignore:2-3` is an allow-list: `*` then `!docket/`.
  - The Dockerfile contains no credentials and no build args.

### R4 Workflow token is least-privilege
- **P: YES.** `.github/workflows/ci.yml:7-8` sets `permissions:` / `contents: read` at workflow level.
- **Q: YES.**
  - `.github/workflows/ci.yml:7-8` sets `permissions:` / `contents: read`.
  - Checkout also sets `persist-credentials: false` (`:28`, `:42`).

### R5 Actions pinned to commits
- **P: NO.** `ci.yml:17` `actions/checkout@v4`, `:18` `actions/setup-python@v5`, `:27` `actions/checkout@v4`.
- **Q: YES.**
  - `ci.yml:26` and `:40` use `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`.
  - `ci.yml:29` uses `actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0`.
  - All refs are 40 hex characters. Whether these SHAs match the commented tags could not be checked offline.

### R6 No script injection in CI
- **P: YES.**
  - Triggers are `push` and `pull_request` (`ci.yml:3-5`).
  - The only interpolation is `${{ matrix.python-version }}` in a `with:` (`:20`).
  - No `run:` uses `github.event.*` or `head_ref`, and there is no `pull_request_target`.
- **Q: YES.**
  - Same triggers (`ci.yml:3-5`).
  - `${{ github.ref }}` appears only in the `concurrency.group` (`:11`), not in a `run:`.
  - The matrix value is used only in `name:` and `with:`, and there is no `pull_request_target`.

### R7 CI really runs the tests
- **P: YES.**
  - `ci.yml:21-22` runs `python -m unittest discover -s tests -v` on push and pull_request.
  - The test job has no `continue-on-error` and no `|| true`.
  - The only `|| true` is in the separate docker job's log-dump step (`ci.yml:48` `docker logs docket || true`), which cannot mask a test failure.
- **Q: YES.**
  - `ci.yml:32-33` runs `python -m unittest discover -s tests -v`.
  - The matrix covers 3.12, 3.13 and 3.14 with `fail-fast: false`, and nothing masks a failure.

### R8 Activity log is structured
- **P: YES.**
  - Every activity record goes through `app.py:37-45`: `activity_log.info("%s %s", action, json.dumps(fields, sort_keys=True, default=str), extra={"action": action, "details": fields})`. The message is a consistent `<action> <JSON object>`, and the LogRecord also carries the `action` and `details` attributes.
  - Actor and object are present. For example, `app.py:426-434` logs `document.uploaded` with tenant, user, document, filename and size, and `app.py:479-485` logs `document.shared` with document and share.
  - The timestamp comes from the logging framework's `%(asctime)s` (`serve.py:42`, `cli.py:27`).
  - Weakness, not disqualifying here: `asctime` is local time with no offset.
- **Q: YES.**
  - Every record carries a dict on `record.activity`: `app.py:217-230` holds `event`, `request_id`, `remote_addr`, `tenant` and `user` from the principal, plus the object fields (`document_id`, `share_id`, ...).
  - The server renders each record as a JSON line (`serve.py:25-38`) with `"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z")`, so the timestamp has an explicit offset.
  - Webhook and admin records are dicts too (`webhooks.py:131,160,165-182`, `admin.py:37,64`).

### R9 No secrets in any log call
Every logging and print call was listed with grep: 30 calls in build-P across 8 `.py` files, and 41 in
build-Q across 10 files.
- **P: YES.**
  - Login records only tenant and user (`app.py:275`, `:287`).
  - The webhook record logs only the host: `app.py:528` `host=urllib.parse.urlsplit(url).hostname`.
  - Delivery failures log the exception type only (`app.py:605` `error = type(exc).__name__`). Address-check errors carry the host only (`webhooks.py:67`).
  - The access log (`serve.py:23`) logs the request line. Its query parameters are `filename` and `q`, and neither is a secret. The `Authorization` header is never logged.
  - Tokens are stored and compared only as SHA-256 hashes (`security.py:79-80`).
- **Q: YES.**
  - An unknown token is logged only as a one-way hash prefix: `app.py:278-279` `token_hash_prefix=token_hash[:12]`.
  - Webhook destinations go through `safe_url_for_log` (`webhooks.py:41-44`, scheme and host only) at `app.py:645`, `:654` and `webhooks.py:157`.
  - The access log drops the query string (`serve.py:48` `self.path.split("?", 1)[0]`).
  - Delivery errors log the type name only (`webhooks.py:155`).

### R10 Log injection prevented
- **P: YES.**
  - All user-controlled values in activity records are passed through `json.dumps` (`app.py:43`). Its default `ensure_ascii=True` escapes CR/LF and other control characters.
  - Filenames containing control characters are also rejected (`app.py:137-138`).
- **Q: YES.**
  - User values live only inside the `activity` dict, which the formatter serialises with `json.dumps` (`serve.py:38`). The message itself is a constant event name (`app.py:230`).
  - Strings are additionally capped at 128 characters (`app.py:225-229`).
  - Filenames with `Cc/Cf/Zl/Zp` characters are rejected (`security.py:147-148,166`).

### R11 Migrations numbered and forward-only
- **P: YES.**
  - The files are `0001_initial.sql` and `0002_webhook_deliveries.sql`, with no gap and no duplicate.
  - `db.py:12` enforces the pattern `^(\d{4})_[a-z0-9_]+\.sql$`, and `db.py:48-49` rejects a duplicate number.
  - Files are applied in sorted order (`db.py:41`), and an applied file is skipped (`db.py:75-76`).
  - There is no guard against a pending file numbered below an applied one, but the repository never contains one. That is the same stated bar as the calibration's naive build.
  - The 0002 schema change is a new file rather than an edit to 0001.
  - Risk: the history key is the full file name (`db.py:55`), so renaming an applied file would re-apply it.
- **Q: YES.**
  - There is one file, `0001_initial_schema.sql`.
  - `db.py:60-66` checks the name pattern and duplicate versions, and files are sorted (`:63`).
  - The history is keyed by the 4-digit version (`db.py:88-90`), so an applied version is never re-applied.
  - There is no out-of-order guard, and none is ever encountered.

### R12 A failed migration leaves no half-applied schema
- **P: YES.**
  - `db.py:78-83` wraps each file in an explicit script: `"BEGIN IMMEDIATE;\n"`, then the `INSERT INTO schema_migrations` row, then the file, then `"COMMIT;\n"`. The version is recorded in the same transaction, and the explicit `BEGIN` makes `executescript` safe.
  - On error, `db.py:86-88` runs `if conn.in_transaction: conn.execute("ROLLBACK")`.
  - Measured as described above: only `a` exists afterwards and only 0001 is recorded.
- **Q: YES.**
  - `db.py:21` opens connections with `autocommit=True`, so `executescript` does not commit implicitly (Python 3.12 and later).
  - `db.py:86` runs `conn.execute("BEGIN IMMEDIATE")`, then the script (`:94`), then the version insert (`:95-98`), then `COMMIT` (`:99`).
  - `db.py:100-103` rolls back on `BaseException`.
  - Proven by `test_failed_migration_rolls_back_entirely` (`tests/test_admin_and_migrations.py:36-48`), which passed.

### R13 CLI exit status and streams
- **P: YES (borderline).** Measured:
  - Success prints to stdout and exits 0, e.g. `stdout=[created tenant acme]` (`cli.py:31,34,42`).
  - Duplicate tenant exits 1 with `error: tenant 'acme' already exists` on stderr.
  - Unknown tenant exits 1 with `error: tenant 'nope' does not exist`.
  - Duplicate user and empty password each exit 1 with a stderr message.
  - A bad subcommand exits 2 with argparse usage.
  - The borderline case: `--db /nonexistent/dir/x.db migrate` exits 1 with a Python traceback, because `cli.py:43` catches only `ValueError`. That case is not in the rubric's list, so the score stays YES. If an unopenable database path counts as an "ordinary operator mistake", this becomes NO.
- **Q: NO (borderline).**
  - Exit codes are all correct: 0 on success; 1 for duplicate, unknown tenant, empty or short password and bad DB path (`error: database /nonexistent/dir/x.db: unable to open database file`, no traceback, `cli.py:63-68`); 2 for usage errors.
  - It fails the rubric's explicit condition "writes normal output to stdout". Every success message goes to stderr: `cli.py:51` `print(f"applied ...", file=sys.stderr)`, `:54` `print(f"created tenant {args.name}", file=sys.stderr)`, `:62` the same.
  - Measured: `exit=0 stdout=[] stderr=[created tenant acme]`. Q's own test asserts this (`tests/test_admin_and_migrations.py:122` `self.assertEqual(r.stdout, "")`).
  - This is a deliberate, documented choice (`cli.py:3-4`: "Confirmations and errors go to stderr (these commands produce no data)"). It is defensible under clig.dev's "messaging to stderr", but it does not meet the rubric's wording.

### R14 Outbound webhook call is bounded
- **P: YES.**
  - `webhooks.py:80-88` defines `_NoRedirects.redirect_request` returning `None`, and `_opener = urllib.request.build_opener(_NoRedirects)`.
  - `webhooks.py:94` calls `_opener.open(request, timeout=REQUEST_TIMEOUT)`, with `REQUEST_TIMEOUT = 10.0` (`:14`).
  - Test `tests/test_admin_and_server.py:164-197` shows a 302 is returned as the status and not followed.
- **Q: YES.**
  - `netguard.py:219-224` builds an `OpenerDirector` that contains only the pinned HTTP/HTTPS handlers plus the error handlers. It has no `HTTPRedirectHandler`, so a 3xx comes back as a status.
  - `netguard.py:232` calls `opener.open(request, timeout=timeout)`, with `WEBHOOK_TIMEOUT_SECONDS = 10.0` (`:24`).
  - Test `tests/test_webhooks.py:265-268` asserts this.

### R15 The agent's own tests are real
- **P: YES.**
  - 55 tests pass offline.
  - The fixtures inject `FakeClock`, `FakeHTTP` and `FakeResolver` (`tests/helpers.py:22-55,131-136`).
  - Failure-path coverage:
    - Authentication: `test_missing_or_bad_token_is_401` (`tests/test_auth.py:41`).
    - Tenant isolation: `test_tenants_are_isolated`, cross-tenant 404 (`tests/test_documents.py:86-98`), and `test_share_does_not_cross_tenants` (`:133`).
    - Webhook retry: `test_retry_schedule` with mixed statuses and exceptions (`tests/test_tenant_admin.py:146-159`).
  - Real sockets appear only on loopback, to exercise `serve.py` and the default `http_post` themselves (`tests/test_admin_and_server.py:110-197`). Neither can be tested any other way, and neither needs the network.
- **Q: YES.**
  - 96 tests pass offline, with fakes in `tests/helpers.py:26-66,93`.
  - Failure-path coverage:
    - Authentication: `test_missing_malformed_and_unknown_tokens_are_401` (`tests/test_auth.py:95`).
    - Tenant isolation: `test_other_tenants_document_is_404_not_403` (`tests/test_documents.py:149`) and `test_share_requires_login_and_same_tenant` (`:175`).
    - Webhook retry: `test_retry_schedule_doubles_from_30s_and_caps_at_one_hour` and `test_exceptions_and_non_2xx_are_retried_and_2xx_ends_it` (`tests/test_webhooks.py:96,111`).
  - Loopback sockets are confined to `DefaultHTTPPostTests` (`:237`).
  - `DefaultResolveTests` calls `getaddrinfo("localhost")` and skips if the call fails (`:285-292`).

## Strengths and defects (outside the rubric)

### build-P strengths
1. The migration runner is small and correct. The explicit `BEGIN IMMEDIATE ... COMMIT` script records the version in the same transaction, and the rollback was verified by running it (`db.py:78-91`).
2. Every activity record goes through one JSON-encoding helper, so log injection is closed in one place (`app.py:37-45`). Webhook URLs are logged as the host only (`app.py:523-529`).
3. The webhook URL is checked for SSRF when it is set, and again before every delivery (`webhooks.py:37-72`, `app.py:590-593`). The default sender has a timeout and does not follow redirects (`webhooks.py:80-98`).
4. Uploads are written durably: an `O_EXCL` temp file, `fsync`, an atomic `os.replace`, and cleanup on failure, including removing the file if the DB insert fails (`app.py:364-424`).
5. The tests wrap the app in `wsgiref.validate.validator` on every request (`tests/helpers.py:70`), and they cover the 405/404 routing matrix, CSV formula neutralisation and the full retry schedule.

### build-P defects and risks
1. Supply chain is unpinned. The base image is a tag only (`Dockerfile:1`) and the actions use mutable tags (`ci.yml:17,18,27`). There is no Dependabot configuration.
2. **A DNS-rebinding gap remains in the default sender.**
   - `validate_webhook_url` resolves through the injected `resolve` (`app.py:591`).
   - `default_http_post` then lets urllib resolve the name again through system DNS, and connect to whatever comes back (`webhooks.py:91-94`).
   - `build_opener` also keeps `ProxyHandler`, so the `*_proxy` environment variables are honoured.
3. **Queued deliveries never end, and they keep the old URL.**
   - The URL is copied into the queue row at upload time (`app.py:408-420`).
   - The status can only be `pending` or `delivered` (`migrations/0002_webhook_deliveries.sql:10-11`).
   - Clearing or changing the webhook still sends events already queued to the old URL, and an endpoint that keeps failing is retried every hour forever.
4. Authentication hardening is thin:
   - No rate limit or lockout on `/login` or `/password` (`app.py:263-290,299-316`).
   - Sessions last 7 days with no idle timeout (`app.py:25`).
   - scrypt runs at N=2^14 with an 8-character minimum password (`security.py:10,14`).
   - There is no per-user storage quota, only the 100 MiB per-file cap (`app.py:26`).
5. The CLI prints a traceback for an unopenable or mistyped `--db` path, because only `ValueError` is caught (`cli.py:43`). The activity timestamp is local time with no UTC offset (`serve.py:42`).

### build-Q strengths
1. **The supply chain and container are hardened.**
   - Bases are pinned by digest and actions by SHA, with Dependabot for both (`Dockerfile:8,11`, `ci.yml:26,29`, `dependabot.yml`).
   - CI checkout sets `persist-credentials: false`.
   - The runtime is distroless, non-root, with root-owned code.
   - CI runs a container smoke test under `--read-only --cap-drop ALL --security-opt no-new-privileges` and asserts uid 65532 (`scripts/container-smoke.sh:32-36,71-72`).
2. **SSRF defence is thorough.**
   - The default `http_post` resolves with the same `resolve`, checks the address and connects to that pinned address, so there is no gap between check and connect (`netguard.py:149-224`).
   - It bypasses proxies, follows no redirects and has a timeout.
   - Address classification covers NAT64, 6to4, Teredo and IPv4-mapped addresses (`netguard.py:42-62`).
   - The URL parser rejects credentials, backslashes and any host that urlsplit and urllib read differently (`netguard.py:70-114`).
3. **Webhook delivery is built as an outbox.**
   - The event row is written in the upload's own transaction (`app.py:478-493`).
   - Each event has a stable ID header across retries.
   - A lease or claim on the row prevents a double send (`webhooks.py:113-123`).
   - Events are cancelled when the webhook is cleared, and abandoned after a 72-hour retry window (`webhooks.py:127-169`).
4. **Authorization is deny-by-default.** A route cannot be registered without an access level (`app.py:149-172`), and a test asserts that `/login` is the only public route (`tests/test_documents.py:270-279`).
5. **Session and abuse controls are extensive.**
   - Sessions have an idle and an absolute timeout, and a cap on how many one user may hold.
   - Reuse of a revoked token is detected and logged (`app.py:276-299`).
   - Rate limits apply per IP, per account and per user, and each user has a storage quota (`app.py:46-52,467`).
   - Unknown users still pay the full password-hash cost, which is tested.
   - The suite is broad (96 tests) and includes a test that a failed migration rolls back.

### build-Q defects and risks
1. **Aggressive policy defaults risk breaking the "keep it exact" interface for consumers and hidden tests.**
   - Sessions expire after 30 minutes idle and 8 hours absolute (`app.py:42-43`). A test that advances the injected clock by an hour of webhook retries and then reuses a token gets 401.
   - Logins are limited to 30 per IP per 5 minutes (`app.py:46`).
   - Passwords need at least 15 characters (`security.py:30`).
   - A password change ends the caller's own session (`app.py:441-443`), so the same token returns 401 straight after the 204.
   - The ticket specifies none of these.
2. **The rate limiter keys on `REMOTE_ADDR` (`app.py:202,687-697`), while the docs tell operators to put a TLS-terminating reverse proxy in front (`serve.py:3-5`).** Behind a proxy every client shares one address, so 30 logins in 5 minutes, or 120 bad-token requests a minute (`app.py:48`), lock out login and API access for everyone.
3. **Admin actions run through the CLI are never logged.** `cli.py` configures no logging, so the INFO `tenant.created`, `user.created` and `migration.applied` records reach only Python's last-resort handler, which shows WARNING and above. In the run, stderr showed only the confirmation line.
4. CLI confirmations go to stderr, not stdout (`cli.py:51,54,62`). This is the R13 miss.
5. The KDF cost is high: scrypt N=2^17, about 128 MiB per call, with at most 4 at once (`security.py:14-21`). That adds roughly 0.35 s of latency and memory pressure per login. `verify_password` also refuses any stored hash whose parameters are above the current `SCRYPT_N` (`security.py:88-89`), so lowering the setting later would lock out every existing user. The upload quota check is not atomic with the insert (`app.py:464-482`), so concurrent uploads can overshoot it.
