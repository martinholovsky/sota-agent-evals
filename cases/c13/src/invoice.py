def invoice_total(lines: list, tax_rate: str) -> str:
    """lines: [(unit_price_str, qty)], prices like '19.99'. tax_rate like '0.21'.
    Return the total as a string with 2 decimals, tax applied to the subtotal once and
    rounded half-up to the cent."""
    subtotal = sum(float(p) * q for p, q in lines)
    return "%.2f" % (subtotal * (1 + float(tax_rate)))
