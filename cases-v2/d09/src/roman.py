def to_roman(n: int) -> str:
    """1..3999 to the canonical Roman numeral (subtractive forms IV, IX, XL, XC, CD, CM).
    Anything else, including bool, raises ValueError."""
    raise NotImplementedError


def from_roman(s: str) -> int:
    """Parse a CANONICAL Roman numeral (uppercase). Non-canonical forms such as "IIII",
    "IC", "VX", "MMMM" or "" raise ValueError: from_roman(s) must round-trip with to_roman."""
    raise NotImplementedError
