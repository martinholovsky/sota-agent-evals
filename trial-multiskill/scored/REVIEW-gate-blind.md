# Blind review: build-K vs build-M (DOC-142, Docket v1)

Scored strictly against REVIEW-RUBRIC.md. Nothing outside this directory was opened and no
file in either build was edited. Python used: 3.14.8 (local). `docker build` was not run;
the Dockerfiles were judged by reading them.

## Scoreboard

| # | Item | build-K | build-M |
|---|------|---------|---------|
| R1 | Base image pinned | YES | YES |
| R2 | Container runs as non-root | YES | YES |
| R3 | Build context minimal, secret-free | YES | YES |
| R4 | Workflow token least-privilege | YES | YES |
| R5 | Actions pinned to commits | YES | YES |
| R6 | No script injection in CI | YES | YES |
| R7 | CI really runs the tests | YES | YES |
| R8 | Activity log is structured | YES* | YES* |
| R9 | No secrets in any log call | YES | YES |
| R10 | Log injection prevented | YES | YES (residual gap noted) |
| R11 | Migrations numbered, forward-only | YES | YES |
| R12 | Failed migration leaves no half-applied schema | YES | YES |
| R13 | CLI exit status and streams | **NO** | YES |
| R14 | Outbound webhook call is bounded | YES | YES |
| R15 | The agent's own tests are real | YES | YES |
| | **YES count** | **14 / 15** | **15 / 15** |

\* R8: both builds identify the actor by tenant plus numeric `user_id`, not by username. I
read `user_id` as satisfying "the actor"; under a strictly literal reading ("tenant +
username") both flip to NO together, so the item does not separate them either way.

R13 is the only item that separates the builds, and it rests on a call about scope: on the
four failures the rubric names, build-K does pass. See the evidence.

## Commands run

- Test suites, from each build root, run unpiped with the exit status captured:
  `python3 -m unittest discover -s tests`
  - build-K: `Ran 88 tests in 23.284s` / `OK`, exit 0
  - build-M: `Ran 62 tests in 6.765s` / `OK`, exit 0
- CLI matrix, run for each build against a fresh temp DB in `_tmp_build-K.tQmk/` and `_tmp_build-M.DHFR/`:
  migrate, create-tenant, duplicate tenant, create-user, duplicate user, unknown tenant,
  empty password, no stdin, unknown subcommand, missing `--db`, `--db` in a directory that does not exist,
  `--db` pointing at a directory.
- build-M HTTPS pinning check: printed `_PinnedHTTPSConnection.__mro__` →
  `['_PinnedHTTPSConnection', 'HTTPSConnection', '_PinnedConnectionMixin', 'HTTPConnection', 'object']`,
  and confirmed that stdlib `HTTPSConnection.connect` calls `super().connect()`. So the pinned
  `connect` really does run beneath the TLS wrap.

## Evidence per item

### R1 Base image pinned
- K YES, `build-K/Dockerfile:4`: `FROM docker.io/library/python:3.14-slim@sha256:9aaa4740...f04802f`
- M YES, `build-M/Dockerfile:4`: `FROM docker.io/library/python:3.14.10-slim-trixie@sha256:9aaa4740...f04802f`
- Both use the same digest. Whether that digest exists in the registry is **unverified** (no network or registry check was run). The rubric asks only for an immutable digest reference.

### R2 Non-root
- K YES. `Dockerfile:10-12` creates uid 10001 and runs `mkdir /data && chown docket:docket /data`. `:18` sets `USER docket:docket` before `ENTRYPOINT` (`:26`). The DB is `DOCKET_DB=/data/docket.db` (`:8`).
- M YES. `Dockerfile:12` runs `install -d -o docket -g docket -m 0750 /data`. `:18` sets `USER 10001:10001` before `ENTRYPOINT` (`:26`), and the DB is `--db /data/docket.db`.

### R3 Build context
- K YES. `.dockerignore:1-2` is `*` then `!docket/`, and `Dockerfile:15` is `COPY ... docket/ /app/docket/`. There are no secrets or build args.
- M YES. `.dockerignore:1-2` is `*` then `!docket/`, and `Dockerfile:16` is `COPY ... docket/ /app/docket/`. There are no secrets or build args.

### R4 Token permissions
- K YES. `ci.yml:8-9` has `permissions:` / `contents: read` at workflow level, and no job widens it.
- M YES. `ci.yml:8-9` is identical.

### R5 Actions pinned
- K YES. `ci.yml:24,37` has `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1` and `:27` has `actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0`. Both SHAs are 40 hex characters.
- M YES. `ci.yml:24,27,37` pins the same two SHAs.
- Whether those SHAs exist upstream, and whether the version comments match them, is **unverified**.

### R6 Script injection
- K YES. The only `${{ }}` expressions are `github.ref` in `concurrency.group` (`:12`, not a `run:`) and `matrix.python-version` in `with:` (`:29`). There is no `pull_request_target`.
- M YES. Same pattern (`:12`, `:29`). Its `run:` steps contain no expressions.

### R7 CI runs tests
- K YES. `on: push [main]` and `pull_request` (`:3-6`); `:31` runs `python -m unittest discover -s tests -v`. The test step has no `continue-on-error` and no `|| true` (`|| true` appears only in the log and cleanup steps, `:67`, `:71-72`).
- M YES. Same triggers; `:31` runs `python -m unittest discover -s tests -v`.

### R8 Structured activity log
- K YES\*. `app.py:118-119` is `activity.info(event, extra={"activity": {"event": event, **fields}})`. `logsetup.py:12-25` renders each record as a JSON object, and `:15` sets an explicit UTC `"ts"`. Example `app.py:446`: `_log("document.uploaded", tenant=p.tenant_name, user_id=p.user_id, document_id=doc_id, ...)`. That gives the action, the actor (tenant name plus `user_id`) and the object. The CLI run confirmed it: `{"ts": "...+00:00", ..., "msg": "user.created", "event": "user.created", "tenant": "acme", "user_id": 1, "role": "admin"}`.
- M YES\*. `activity.py:27-31` writes `json.dumps(record, ensure_ascii=True, sort_keys=True)` as the message, with an `"event"` key. The timestamp comes from the logging framework: `record.created`, and in `serve.py:86` `%(asctime)s`. Example `app.py:591-594`: `activity("document.uploaded", user_id=..., tenant_id=..., document_id=doc_id, ...)`.
- \* Neither build logs the username as the actor; see the note under the table.

### R9 No secrets in logs
I read every logging call in both builds.
- K YES.
  - Tokens are never logged. `app.py:278` logs `session: th[:12]`, a prefix of the SHA-256 token hash (a one-way hash).
  - Failed logins log only the hashed account tag (`:323`).
  - Webhook changes log the host only (`:573-575`: "Host only: a URL path or query can carry the receiver's own secret").
  - The access log strips the query string (`serve.py:30-31`).
  - Delivery errors log only `type(exc).__name__` (`:657`).
  - The e2e test asserts that neither the password nor the token appears in server stderr (`tests/test_cli_and_server.py:139-140`).
- M YES.
  - Webhook changes log scheme and host only (`app.py:754-755`).
  - Delivery errors log only `type(exc).__name__` (`:374`).
  - Field names that look like credentials are redacted centrally (`activity.py:16,30`).
  - `share_id` is logged in full (`app.py:705,725`). It is not a credential (opening a share needs a same-tenant login), so the item still passes.
  - `webhook-secret` prints the secret to stdout as CLI output, not through a log call.

### R10 Log injection
- K YES. All `docket.*` output goes through `JSONFormatter` (`logsetup.py:25`, `json.dumps(..., ensure_ascii=True)`), including the access log (`serve.py:32-34`), `log_message` (`:37`) and `errlog.exception` (`app.py:165`). Filenames are never logged. Route ids are restricted to `[A-Za-z0-9_-]{1,64}` (`app.py:123`).
- M YES, with a residual gap.
  - Activity values are JSON-encoded at the single writer (`activity.py:31`).
  - The access log uses `%r` (`serve.py:40`: "%r-escaped so a crafted request line cannot forge log lines").
  - Residual gap: `app.py:224` `log.exception("unhandled error on %s %s", ..., environ.get("PATH_INFO"))` interpolates the URL-decoded `PATH_INFO` raw into a plain-text formatter (`serve.py:86`). The routes `[^/]+` (`app.py:805-807`) accept `%0A`. It only fires on an unhandled 500, so it is hard to reach, but it is not encoded.

### R11 Migrations
- K YES. The only file is `0001_initial_schema.sql`, and `db.py:14` enforces `^(\d{4})_[a-z0-9_]+\.sql$`. Duplicates are refused (`:59-60`), files run in sorted order (`:62`), versions are recorded (`:100-102`), and an applied version is skipped (`:94-96`).
  - K has no gap check and no refusal for a pending file numbered below an applied one. With a single file it never meets that case, which is yes on the rubric's stated bar (the same basis as the calibration "naive" row).
  - The file header says "never edit after release, add 0002_*.sql instead".
- M YES. The only file is `0001_initial.sql`. `db.py:59-60` refuses anything except a contiguous `1..N` (no gaps, no duplicates). Applied migrations are checksummed, and an edited one is refused (`:89-91`).

### R12 Atomic migration
- K YES. `db.py:92-102` runs each migration in `with transaction(conn):` (`BEGIN IMMEDIATE` … `ROLLBACK` on error, `:36-44`). Statements run through `conn.execute` one at a time (no `executescript`), and the version `INSERT` happens inside the same block. `tests/test_migrations.py:35-49` checks a broken `0002` and passes.
- M YES. `db.py:85-99` uses `transaction(conn, immediate=True)` and then `conn.executescript(sql)`. The connection is opened with `autocommit=True` (`:30`), and with that setting `executescript` issues no implicit COMMIT (comment `:93-94`, consistent with the Python docs). The version is inserted in the same transaction. `tests/test_admin_and_migrations.py:57-68` checks that a broken script leaves no `half` table, and passes.

### R13 CLI exit status and streams
- K **NO**.
  - All four failures the rubric names behave correctly: exit 1 with a single stderr line. Duplicate tenant gives `docket: error: tenant 'acme' already exists`. Duplicate user, unknown tenant and empty password (`password must be at least 8 characters`) do the same.
  - Bad arguments exit 2 through argparse, and success output goes to stdout.
  - However, two ordinary operator mistakes print a Python traceback with exit 1:
    - `--db /nonexistent-dir/x/d.db migrate` (`FileNotFoundError` from `db.py:81` `mkdir`)
    - `--db <a directory> create-tenant x`
  - Cause: `cli.py:55` catches only `admin.AdminError`, so `OSError`, `sqlite3.Error` and `MigrationError` escape.
  - If the item is read as covering only the four listed cases, K would be YES.
- M YES.
  - The same matrix gives exit 1 with one-line errors for every failure, including the two above: `error: [Errno 2] No such file or directory: '/nonexistent-dir/x/d.db'` and `error: [Errno 21] Is a directory: ...`.
  - `cli.py:57` catches `(admin.AdminError, MigrationError, sqlite3.Error, OSError)`. Usage errors exit 2, and output goes to stdout.

### R14 Bounded webhook call
- K YES. `webhooks.py:19` sets `HTTP_TIMEOUT = 10.0`, used at `:112` (`opener.open(req, timeout=timeout)`). `_NoRedirect.redirect_request` returns `None` (`:63-65`), so a 3xx is returned as a failure. The opener is built by hand with `ProxyHandler({})` (`:105-109`). `tests/test_transport.py` covers redirects on loopback.
- M YES. `webhooks.py:25` sets `HTTP_TIMEOUT_S = 10.0`, used at `:226`. The hand-built `OpenerDirector` has no redirect handler and no proxy handler (`:222-224`, docstring `:214-216`). `tests/test_webhooks.py:115` is `test_exception_and_redirect_are_failures`.

### R15 Tests are real
- K YES. Offline, 88 tests pass. App tests inject `FakeClock`, `FakeHTTP` and `FakeDNS` (`tests/support.py:23-57`). The failure paths are:
  - 401: `test_auth.py:84` `test_missing_malformed_and_unknown_tokens_are_401`
  - tenant isolation: `test_documents.py:125` `test_other_tenant_cannot_download_list_or_share`
  - webhook retry: `test_webhooks.py:92` and `:104`
  - Note: `test_cli_and_server.py:84-144` starts a real `docket.serve` subprocess on loopback and polls with `time.sleep`, and `test_transport.py` uses a loopback HTTP server to test the default `http_post`. Both are offline and test code that the injection points cannot reach.
- M YES. Offline, 62 tests pass. App tests inject `FakeClock` and `RecordingPost` (`tests/helpers.py:30-55`). The failure paths are:
  - 401: `test_auth.py:88`
  - tenant isolation: `test_documents.py:160` `test_cross_tenant_access_is_indistinguishable_from_missing`
  - webhook retry: `test_webhooks.py:99` and `:115`
  - The only loopback use is the default-transport test (`test_webhooks.py:198-217`).

## Questions (a)–(c)

**(a) Client address for IP-keyed limits, and expected deployment**
- K: `app.py:232-242` `_client` uses `REMOTE_ADDR`, unless the peer is in `DOCKET_TRUSTED_PROXIES` (`:42-43`, a comma-separated IP list from the environment). In that case it takes the rightmost `X-Forwarded-For` hop that is not a trusted proxy. The per-source login limit is 30 attempts per minute (`:36`).
- M: `app.py:230-237` `_client_ip` uses `REMOTE_ADDR` unless `--trusted-proxies N` is greater than 0 (`serve.py:80-83`). In that case it takes `hops[-N]` from `X-Forwarded-For`. The per-source login limit is 30 attempts per 5 minutes (`:49`).
- Both builds expect a TLS-terminating reverse proxy in front: K `serve.py:3-4` and README:32-34; M `serve.py:3-4`, `Dockerfile:25` and README:46-52.
- In both, the shipped default trusts no proxy. Deployed behind a proxy as documented, every client therefore shares the proxy's single source bucket until the operator sets the env var or flag. That is a global login lockout reachable by any one client. M's `ENTRYPOINT` (`Dockerfile:26`) bakes in no `--trusted-proxies`, so the operator has to append it.
- Both also lock an account after repeated failures, even when the correct password is then given:
  - K: 5 failures per 15 minutes (`app.py:35`, `:309-312`)
  - M: 10 failures per 15 minutes (`app.py:50`, `:446-448`)
  - Anyone who knows a tenant and username can therefore keep that account locked out (targeted denial of service).

**(b) DNS rebinding and whether retries end**
- Both default `http_post` implementations resolve the host, require every address to be public, and connect the TCP socket to the checked IP. The Host header, SNI and certificate check still use the hostname.
  - K: `webhooks.py:44-60`, `:97`
  - M: `webhooks.py:165-184`, `:221`; the MRO was verified above
- Both also re-check the destination at every attempt with the injected `resolve` (K `app.py:644-645`, M `app.py:358`). Neither follows redirects.
- Difference: K's default transport resolves with `socket.getaddrinfo` (`default_http_post = make_http_post()`, `webhooks.py:122`) and not with the injected `resolve`. The ticket says "The app uses [resolve] for any DNS lookup it does". M passes the injected `resolve` into the default transport (`app.py:829-830`).
- Retries end in both builds, 72 hours after the event was queued:
  - K: `GIVE_UP_AFTER` (`webhooks.py:18`, `app.py:664`), status `failed`
  - M: `DELIVERY_MAX_AGE_S` (`webhooks.py:24`, `app.py:382`), status `abandoned`
- Both cancel queued events once the webhook is cleared: K at attempt time (`app.py:634-638`), M at clear time (`app.py:737-740`).

**(c) Pinning**
- Both pin the base image by digest (`Dockerfile:4`) and every action by full 40-hex SHA (`ci.yml:24,27,37`). No unpinned `uses:` appears in either build.

## Notable strengths and defects (beyond the rubric)

### build-K

Strengths
1. A DNS-rebinding-safe default transport that never follows redirects and ignores proxy environment variables. The destination is also re-checked at each attempt (`webhooks.py:38-119`, `app.py:644-645`).
2. Durable webhook outbox: the delivery row is written in the upload's own transaction, a row is claimed with a lease so a crash causes a retry rather than a lost event, and delivery gives up after 72 hours (`app.py:426-436`, `:626-632`, `:664-671`).
3. The log pipeline is a JSON formatter with an explicit UTC timestamp and no query strings. An e2e test asserts that neither password nor token leaks into server stderr (`logsetup.py:12-25`, `serve.py:29-34`, `tests/test_cli_and_server.py:134-142`).
4. The client address is derived correctly from a proxy-IP allowlist (rightmost untrusted hop) (`app.py:232-242`).
5. The CI container job builds the image, runs a login and upload smoke test, and asserts the image user (`ci.yml:33-64`).

Defects and risks
1. CLI tracebacks on bad `--db` paths, because only `AdminError` is caught (`cli.py:55`). This is the R13 failure.
2. A per-account lockout that blocks even the correct password enables targeted lockout of known accounts (`app.py:309-312`). Behind the documented proxy, with `DOCKET_TRUSTED_PROXIES` unset, the per-source limiter becomes one global bucket (`app.py:42-43`, `:299-302`).
3. The default `http_post` ignores the injected `resolve` (`webhooks.py:122`, `app.py:711`), which contradicts the ticket's "any DNS lookup" contract.
4. `run_pending_deliveries` caps a run at 500 due rows (`app.py:44`, `:617`), while the interface says it performs every due attempt.
5. The activity log identifies the actor by `user_id` and not by username, and failed logins carry only a hashed account tag (`app.py:323`). That makes an incident timeline harder to read without a database join.

### build-M

Strengths
1. A DNS-rebinding-safe default transport that is built with the injected `resolve`, never follows redirects, has no proxy handler and returns every status without raising (`webhooks.py:164-234`, `app.py:829-830`).
2. Migrations are guarded against gaps, duplicates and edits to an applied file (checksum) (`db.py:58-60`, `:84-92`).
3. Deny-by-default route policy (`PUBLIC`/`MEMBER`/`ADMIN`) is enforced in the dispatcher before any handler runs (`app.py:249-261`, `:800-811`).
4. The CLI catches `OSError`, `sqlite3.Error` and `MigrationError` as well as admin errors, so no traceback reaches the operator (`cli.py:57`).
5. Webhooks are signed (Standard-Webhooks HMAC, with a per-tenant secret that can be rotated). The container smoke test runs the image with `--read-only --cap-drop ALL --security-opt no-new-privileges` (`webhooks.py:157-161`, `admin.py:57-73`, `scripts/container-smoke.sh:25-27`).

Defects and risks
1. Same proxy and lockout exposure as K. The default `--trusted-proxies 0` (and the `ENTRYPOINT`, `Dockerfile:26`) collapses every client behind the proxy into one 30-per-5-minutes login bucket (`app.py:49`, `:438-440`). The per-account lockout blocks even the correct password (`app.py:446-448`).
2. scrypt at N=2^17 (128 MiB) behind a 4-slot semaphore means unauthenticated login attempts, including dummy-hash checks for unknown users, queue every login behind the semaphore. That makes login an amplified denial-of-service lever (`security.py:18-24`, `:41-44`, `app.py:455`).
3. Departures from the ticket's interface that hidden tests may trip on:
   - A 15-character minimum password, also applied to `admin.create_user` (`security.py:26`, `admin.py:37`).
   - Requests without `Content-Type: application/json` get a 415, and unknown JSON fields get a 400 (`app.py:158-160`, `:173-175`).
   - `GET /documents` is silently capped at 1000 rows and adds `next_cursor` (`app.py:45`, `:623-641`).
4. `log.exception` writes the raw URL-decoded `PATH_INFO` through a plain-text formatter (`app.py:224`, `serve.py:86`). This is the residual log-injection gap noted under R10.
5. A stored file missing from disk produces an unhandled `FileNotFoundError` and so a 500 (`app.py:657`), where K returns 404. Also, the upload `os.replace`s the file into place before the database transaction commits (`app.py:562-564`), so a crash between those two steps leaves an orphaned file.

## Housekeeping
Running the suites created `__pycache__/` directories inside both builds. The CLI checks left
`_tmp_build-K.tQmk/` and `_tmp_build-M.DHFR/`, and the test logs `_k_tests.log` and
`_m_tests.log` sit in this directory. None of them were removed.
