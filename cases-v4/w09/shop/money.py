"""Money is integer cents everywhere. Never use floats for amounts."""

ROUNDING_NOTE = "all percentages are applied with round-half-up to the cent"


def pct_of(cents: int, pct: int) -> int:
    """`pct` percent of `cents`, rounded half up to the cent. pct is an int 0..100."""
    if not 0 <= pct <= 100:
        raise ValueError("pct out of range: %r" % pct)
    return (cents * pct + 50) // 100


def fmt(cents: int, currency: str = "USD") -> str:
    """'$12.34' / '-$0.50'. Only USD is supported."""
    if currency != "USD":
        raise ValueError("unsupported currency: %r" % currency)
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s$%d.%02d" % (sign, cents // 100, cents % 100)


def parse(text: str) -> int:
    """'12.34' -> 1234; '12' -> 1200; '0.5' -> 50. Rejects negatives and > 2 decimals."""
    text = text.strip()
    if not text or text.startswith("-"):
        raise ValueError("bad amount: %r" % text)
    whole, _, frac = text.partition(".")
    if not whole.isdigit() or (frac and (not frac.isdigit() or len(frac) > 2)):
        raise ValueError("bad amount: %r" % text)
    return int(whole) * 100 + int((frac + "00")[:2] if frac else 0)
