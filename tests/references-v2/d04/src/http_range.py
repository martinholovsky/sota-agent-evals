import re

_ONE = re.compile(r"(\d*)-(\d*)")


def parse_range(header: str, size: int) -> list:
    if not header.startswith("bytes="):
        raise ValueError(header)
    out = []
    parts = header[len("bytes="):].split(",")
    for p in parts:
        m = _ONE.fullmatch(p.strip())
        if not m or (not m.group(1) and not m.group(2)):
            raise ValueError(p)
        a, b = m.group(1), m.group(2)
        if not a:
            n = int(b)
            if n == 0:
                raise ValueError(p)
            out.append((max(0, size - n), size - 1))
            continue
        start = int(a)
        end = int(b) if b else size - 1
        if b and start > end:
            raise ValueError(p)
        if start >= size:
            continue
        out.append((start, min(end, size - 1)))
    if not out:
        raise ValueError("unsatisfiable")
    return out
