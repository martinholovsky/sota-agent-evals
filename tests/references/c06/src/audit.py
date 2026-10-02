import logging
import re

log = logging.getLogger("audit")
SENSITIVE = {"authorization", "x-api-key", "cookie", "set-cookie", "proxy-authorization"}
QUERY = re.compile(r"(?i)\b(token|access_token|api_key|key|password|secret|code)=[^&#]*")


def log_request(method: str, url: str, headers: dict) -> None:
    safe = {k: ("[REDACTED]" if k.lower() in SENSITIVE else v) for k, v in headers.items()}
    log.info("request %s %s headers=%s", method, QUERY.sub(lambda m: m.group(1) + "=[REDACTED]", url), safe)
