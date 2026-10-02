def format_price(cents: int) -> str:
    """'$12.34' for 1234; negative amounts as '-$0.50'."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s$%d.%02d" % (sign, cents // 100, cents % 100)
