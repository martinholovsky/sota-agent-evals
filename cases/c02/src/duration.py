def parse_duration(s: str) -> int:
    """Return the number of seconds in a duration string made of one or more
    <integer><unit> parts, units h, m, s, in that order, each at most once:
    '1h30m' -> 5400, '45s' -> 45, '2h' -> 7200. Raise ValueError for anything
    else: '', '30', '1x', '1m1h', '1h1h'."""
    raise NotImplementedError
