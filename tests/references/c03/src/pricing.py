import warnings


def total_price(qty: int, unit_cents: int, discount_pct: int = 0) -> int:
    gross = qty * unit_cents
    return (gross * (100 - discount_pct) + 50) // 100


def calc(*a, **k):
    warnings.warn("calc is deprecated; use total_price", DeprecationWarning, stacklevel=2)
    return total_price(*a, **k)
