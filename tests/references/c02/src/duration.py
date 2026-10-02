import re

_RX = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")


def parse_duration(s: str) -> int:
    m = _RX.fullmatch(s)
    if not s or not m or not any(m.groups()):
        raise ValueError(s)
    h, mi, se = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + se
