import re

SKU = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def is_valid_sku(s: str) -> bool:
    return SKU.fullmatch(s) is not None
