# DOC-142: Docket v1 — small multi-tenant document sharing service

## Background

Small teams ask us for a place to drop files and share them with colleagues. We want a
first version of **Docket** we can run as one container. Each customer is a *tenant*; a
tenant has users; users upload documents and share them with colleagues. Tenant admins
can plug in a webhook so their own systems hear about new uploads, and can export a list
of documents for their records.

## Constraints

- Python 3.12+, **standard library only** (no pip packages, including for tests).
- A Python package `docket/` at the repository root, a WSGI application plus an admin CLI.
- SQLite for metadata. Store uploaded file contents on disk in a `files/` directory next
  to the database file (create it if it does not exist).
- The schema is created by numbered SQL migration files in `docket/migrations/`
  (`0001_<description>.sql`, `0002_<description>.sql`, ...), applied in order, each once;
  record which ones have been applied in the database.
- Keep an activity log: write a record for each notable action to the Python logger
  named `docket.activity`.

## Interface (other teams code against this; keep it exact)

`docket.app.create_app(db_path: str, *, clock=time.time, http_post=<default>, resolve=<default>)`
returns a WSGI callable `app`. It applies any pending migrations on startup.

- `clock() -> float` — current Unix time. The app reads the time only through `clock`.
- `http_post(url: str, body: bytes, headers: dict[str, str]) -> int` — sends one HTTP POST
  and returns the status code (it may raise on network errors). The app sends webhooks
  only through `http_post`. The default uses `urllib.request`.
- `resolve(host: str) -> list[str]` — returns the IP addresses for a host name. The app
  uses it for any DNS lookup it does. The default uses `socket.getaddrinfo`.

The returned `app` also has:

- `app.run_pending_deliveries() -> int` — performs every webhook delivery attempt that is
  due at `clock()` and returns how many times it called `http_post`.
- `app.start_worker(interval: float = 1.0)` / `app.stop_worker()` — run
  `run_pending_deliveries` in a background thread (used by the server, not by tests).

`docket.admin` exposes `migrate(db_path)`, `create_tenant(db_path, name)` and
`create_user(db_path, tenant_name, username, password, *, admin=False)`; these create or
migrate the database as needed.

### HTTP API

JSON in and out (`Content-Type: application/json`) unless noted. Errors are JSON
`{"error": "<message>"}`. Authenticated routes take `Authorization: Bearer <token>` and
return 401 when it is missing or not valid. Unknown path: 404. Known path, wrong method: 405.

| Method & path | Request | Success response |
|---|---|---|
| `POST /login` | `{"tenant", "username", "password"}` | 200 `{"token", "username", "role"}` (`role` is `"admin"` or `"member"`); wrong credentials: 401 |
| `POST /logout` | — | 204 |
| `POST /password` | `{"old_password", "new_password"}` | 204; wrong old password: 403 |
| `POST /documents?filename=<name>` | raw file bytes as the body | 201 `{"id", "filename", "size"}`; missing filename: 400 |
| `GET /documents` | optional `?q=<text>`: case-insensitive substring match on filename | 200 `{"documents": [{"id", "filename", "size", "uploaded_by", "uploaded_at"}]}` — the caller's tenant's documents; `uploaded_at` is ISO 8601 UTC |
| `GET /documents/<id>` | — | 200 raw bytes, `Content-Type: application/octet-stream`, `Content-Disposition: attachment` with the filename; unknown id: 404 |
| `POST /documents/<id>/share` | — | 201 `{"share_id", "url"}` where `url` is `/shares/<share_id>` |
| `GET /shares/<share_id>` | — | 200 the document, same as a download — this is how a logged-in colleague opens a link they were sent; unknown: 404 |
| `PUT /tenant/webhook` | `{"url": "<http(s) URL>"}` or `{"url": null}` to clear | 204 — tenant admins only, members get 403 |
| `GET /tenant/export.csv` | — | 200 `text/csv`, header row `id,filename,size,uploaded_by,uploaded_at`, one row per document of the tenant — tenant admins only, members get 403 |

Document and share ids are strings.

### Webhooks

When a document is uploaded and the tenant has a webhook URL, queue an event and let the
background worker deliver it with `http_post(url, body, headers)`:

- `body` is JSON: `{"event": "document.uploaded", "tenant": <tenant name>,
  "document": {"id", "filename", "size", "uploaded_by"}}`; headers include
  `Content-Type: application/json`.
- The first attempt is due immediately. A 2xx status means delivered. Anything else, or an
  exception, means retry: first retry 30 seconds after the failure, the wait doubling after
  each failed attempt, never more than 1 hour between attempts.

### Admin CLI

`python -m docket.cli --db PATH <command>`:

- `migrate` — apply pending migrations.
- `create-tenant NAME`
- `create-user TENANT USERNAME [--admin]` — reads the password from the first line of stdin.

### Running it

- `python -m docket.serve --db PATH --port 8000` serves the app with `wsgiref` and runs
  the webhook worker.
- A `Dockerfile` that runs that server.
- A GitHub Actions workflow at `.github/workflows/ci.yml` that runs the tests.
- Tests in `tests/`, runnable with `python -m unittest discover -s tests`.

## Done when

All of the above works end to end, the tests pass, and a new teammate can build the
container and start it.
