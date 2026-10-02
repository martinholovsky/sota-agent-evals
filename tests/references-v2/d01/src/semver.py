import re

_RX = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")


def _parse(v):
    m = _RX.fullmatch(v)
    if not m:
        raise ValueError(v)
    return tuple(int(x) for x in m.group(1, 2, 3)), (m.group(4).split(".") if m.group(4) else None)


def _cmp(x, y):
    return (x > y) - (x < y)


def compare(a: str, b: str) -> int:
    (ca, pa), (cb, pb) = _parse(a), _parse(b)
    if ca != cb:
        return _cmp(ca, cb)
    if pa is None or pb is None:
        return _cmp(pa is None, pb is None)
    for x, y in zip(pa, pb):
        xn, yn = x.isdigit(), y.isdigit()
        if xn and yn:
            r = _cmp(int(x), int(y))
        elif xn != yn:
            r = -1 if xn else 1
        else:
            r = _cmp(x, y)
        if r:
            return r
    return _cmp(len(pa), len(pb))
