_TABLE = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
_ALL = {}


def to_roman(n: int) -> str:
    if type(n) is not int or not 1 <= n <= 3999:
        raise ValueError(n)
    out = []
    for v, s in _TABLE:
        while n >= v:
            out.append(s); n -= v
    return "".join(out)


def from_roman(s: str) -> int:
    if not _ALL:
        _ALL.update({to_roman(i): i for i in range(1, 4000)})
    if s not in _ALL:
        raise ValueError(s)
    return _ALL[s]
