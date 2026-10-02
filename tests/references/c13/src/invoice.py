from decimal import ROUND_HALF_UP, Decimal


def invoice_total(lines: list, tax_rate: str) -> str:
    subtotal = sum((Decimal(p) * q for p, q in lines), Decimal("0"))
    total = (subtotal * (1 + Decimal(tax_rate))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return str(total)
