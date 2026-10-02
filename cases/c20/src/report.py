from src.money import format_price


def line(name: str, cents: int) -> str:
    return "%s: %s" % (name, format_price(cents))
