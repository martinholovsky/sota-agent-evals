def calc(qty: int, unit_cents: int, discount_pct: int = 0) -> int:
    """Total in cents, discount applied once, rounded half up."""
    gross = qty * unit_cents
    return (gross * (100 - discount_pct) + 50) // 100
