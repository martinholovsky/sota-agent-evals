import re

# A SKU is one or more groups of letters/digits separated by single hyphens: AB-12-C
SKU = re.compile(r"^([A-Za-z0-9]+-?)+$")


def is_valid_sku(s: str) -> bool:
    return bool(SKU.match(s)) and not s.endswith("-")
