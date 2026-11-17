# Base image pinned by digest (python:3.12-slim, resolved 2026-11-17); bump deliberately.
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system --gid 10001 docket \
 && useradd --system --uid 10001 --gid docket --home-dir /nonexistent --shell /usr/sbin/nologin docket \
 && mkdir -p /data && chown docket:docket /data

WORKDIR /app
COPY docket/ ./docket/

USER 10001:10001
VOLUME ["/data"]
EXPOSE 8000
ENTRYPOINT ["python", "-m", "docket.serve", "--db", "/data/docket.db", "--host", "0.0.0.0", "--port", "8000"]
