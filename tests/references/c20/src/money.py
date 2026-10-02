SYMBOLS = {"USD": "$", "EUR": "€"}


def format_price(cents: int, currency: str = "USD") -> str:
    if currency not in SYMBOLS:
        raise ValueError("unsupported currency: %r" % currency)
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s%s%d.%02d" % (sign, SYMBOLS[currency], cents // 100, cents % 100)
