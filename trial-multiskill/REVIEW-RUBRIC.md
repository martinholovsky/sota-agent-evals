# Docket trial: review rubric (things the hidden tests cannot check)

Score each item **yes** or **no** by reading the agent's repository. "Yes" requires every
condition in its "counts as yes" column; anything less is "no". No partial credit, and no
credit for a comment or TODO that promises the control. Sources are external only.

| # | Item | Counts as yes | Source |
|---|------|---------------|--------|
| R1 | Base image pinned | The `FROM` line names an immutable digest (`image@sha256:...`), optionally with a tag. A tag alone (`python:3.12`, `python:3.12-slim`) is **no**. | Docker docs, *Building best practices*, "Pin base image versions" (docs.docker.com/build/building/best-practices/); OpenSSF Scorecard, *Pinned-Dependencies* check |
| R2 | Container runs as non-root | The final stage sets `USER` to a non-root user or UID (not `root`, not `0`) before `CMD`/`ENTRYPOINT`, and that user can write the database location (e.g. a chowned data directory or volume). | Docker docs, *Building best practices*, "USER" ("If a service can run without privileges, use USER to change to a non-root user"); CIS Docker Benchmark, section 4 (container images and build file) |
| R3 | Build context is minimal and secret-free | The image copies only what it needs (the package, not `COPY . .` of the whole repo), **or** a `.dockerignore` excludes at least `.git`, databases and local data; no credential, key or password appears in the Dockerfile or build args. | Docker docs, *Building best practices*, "Exclude with .dockerignore"; CIS Docker Benchmark, section 4 (secrets not stored in Dockerfiles) |
| R4 | Workflow token is least-privilege | `.github/workflows/ci.yml` declares `permissions:` at workflow or job level, granting no more than `contents: read` for a test job (no `write-all`, no write scopes it does not use). Omitting `permissions:` is **no** (the default can be read-write depending on repository settings). | GitHub Docs, *Secure use reference* (docs.github.com/en/actions/reference/security/secure-use), "least privilege" for `GITHUB_TOKEN`; GitHub Docs, *Controlling permissions for GITHUB_TOKEN* |
| R5 | Actions pinned to commits | Every `uses:` that references an action outside the repository is pinned to a full-length 40-hex commit SHA (a trailing `# vX.Y.Z` comment is fine). Any `@v4`, `@main` or short SHA is **no**. | GitHub Docs, *Secure use reference*, "Pin actions to a full-length commit SHA"; OpenSSF Scorecard, *Pinned-Dependencies* |
| R6 | No script injection in CI | No `run:` step interpolates attacker-influenced contexts (`${{ github.event.* }}`, `github.head_ref`, issue/PR titles or bodies) directly into shell; the workflow does not combine `pull_request_target` with a checkout of the PR head. A workflow that uses none of these trivially passes. | GitHub Docs, *Secure use reference*, "script injection" |
| R7 | CI really runs the tests | A job runs the project's test command (`python -m unittest discover -s tests` or equivalent) on push and/or pull_request, and a failing test fails the job (no `continue-on-error: true`, no `|| true`). | GitHub Docs, *Workflow syntax for GitHub Actions* (`on`, `jobs.<id>.steps[*].continue-on-error`) |
| R8 | Activity log is structured | Each `docket.activity` record is machine-parseable (JSON object or consistent key=value), and carries at least the action, the actor (tenant + username where there is one) and the object acted on; the timestamp comes from the logging framework or an explicit UTC field. Free-text sentences only (`"user alice uploaded x"`) is **no**. | ASVS 5.0 V16.2.1 (when/where/who/what metadata), V16.2.2 (UTC or explicit offset), V16.2.4 (logs readable by the log processor); OWASP Logging Cheat Sheet, "Which events to log" / "Event attributes" |
| R9 | No secrets in any log call | Reading every logging call in the code (not only `docket.activity`): none can emit a password, a session token, a token-derived value that is not a one-way hash, or a full webhook URL with its query string. The hidden test samples a few flows; this item covers all of them. | ASVS 5.0 V16.2.5; OWASP Logging Cheat Sheet, "Data to exclude" (session identification values, access tokens, authentication passwords) |
| R10 | Log injection prevented | User-controlled values (usernames, filenames, URLs) are encoded before logging (e.g. JSON-encoded fields, or CR/LF escaped), so a filename containing `\n` cannot forge a second log line. | ASVS 5.0 V16.4.1; CWE-117 |
| R11 | Migrations numbered and forward-only | Files under `docket/migrations/` are named `NNNN_description.sql` with no gaps or duplicates; the runner applies them in numeric order, records each applied version, never re-applies one, and either refuses or never encounters a pending file numbered below an applied one. Applied migrations are not edited to change the schema (a later change is a new file). | Flyway documentation, *Versioned migrations* (applied in order, exactly once; validated against the history table); Ambler & Sadalage, *Refactoring Databases* (evolutionary schema changes as ordered, versioned scripts) |
| R12 | A failed migration leaves no half-applied schema | Each migration (or the whole pending set) runs inside a transaction that is rolled back on error, and the version is recorded in the same transaction. Note `sqlite3.Connection.executescript` commits any pending transaction first, so a runner built on it needs an explicit `BEGIN` inside the script or equivalent handling. | SQLite documentation, *Transaction* (lang_transaction.html; DDL is transactional); Python docs, `sqlite3.Connection.executescript` |
| R13 | CLI exit status and streams | `python -m docket.cli` exits 0 on success and non-zero on failure (unknown tenant, duplicate user, empty password, bad arguments), writes the error message to **stderr** without a Python traceback, and writes normal output to stdout. An uncaught exception (traceback, exit 1) for an ordinary operator mistake is **no**. | POSIX.1-2024 XCU 2.8.2 "Exit Status for Commands"; Python docs, `argparse` (usage errors exit 2) and `sys.exit`; Command Line Interface Guidelines (clig.dev), "Errors" and "Output" |
| R14 | Outbound webhook call is bounded | The **default** `http_post` sets a finite timeout and does not follow HTTP redirects (or re-validates every redirect target with the same destination check). | OWASP SSRF Prevention Cheat Sheet ("disable the support for the following of the redirection"); ASVS 5.0 V13.1.3 / V16.5.2; Python docs, `urllib.request.urlopen` `timeout` |
| R15 | The agent's own tests are real | `tests/` runs offline with `python -m unittest discover -s tests` and passes; it uses the injected `clock`/`http_post`/`resolve` rather than real time, sockets or DNS; and it contains at least one failure-path test for each of: authentication (401), tenant isolation (403/404 across tenants), and webhook retry. Happy-path-only suites are **no**. | Python docs, `unittest`; OWASP Web Security Testing Guide, WSTG-ATHZ-04 (testing for insecure direct object references) |

## How the two calibration solutions score (author's reading, 2026-11-17)

| # | reference | naive | Note |
|---|-----------|-------|------|
| R1 | yes | no | naive: `FROM python:3.12` |
| R2 | yes | no | naive: no `USER` |
| R3 | yes | no | naive: `COPY . .`, no `.dockerignore` |
| R4 | yes | no | naive: no `permissions:` |
| R5 | yes | no | naive: `actions/checkout@v4`, `actions/setup-python@v5` |
| R6 | yes | yes | neither interpolates untrusted contexts |
| R7 | yes | yes | both run unittest on push/PR |
| R8 | yes | no | naive: free-text `%s` messages |
| R9 | yes | no | naive logs the full webhook URL (`set webhook to %s`) |
| R10 | yes | no | naive interpolates filenames raw |
| R11 | yes | yes | naive: numbered, applied once, but no out-of-order guard; it never meets one, so yes on the stated bar |
| R12 | yes | no | naive uses `executescript` and records the version afterwards, outside any transaction |
| R13 | yes | no | naive: unknown tenant or duplicate tenant raises a traceback |
| R14 | yes | no | naive: `urlopen` with no timeout, default redirect handler |
| R15 | yes | no | naive's 3 tests are happy-path only |

R6 and R7 do not separate these two solutions; they exist to catch an agent that writes a
worse workflow than the naive one.
