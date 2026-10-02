import logging

log = logging.getLogger("audit")


def log_request(method: str, url: str, headers: dict) -> None:
    log.info("request %s %s headers=%s", method, url, headers)
