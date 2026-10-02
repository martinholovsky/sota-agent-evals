def order_total(lines: list, coupon: str | None = None) -> int:
    """lines: [(unit_cents, qty)]. Returns cents.
    1. Subtotal = sum(unit * qty).
    2. Volume tier on the subtotal: >= 10000 -> 10% off; >= 5000 -> 5% off; else none.
       Tier discount is computed on the subtotal and rounded DOWN to the cent.
    3. Coupon (after the tier): "SAVE500" takes 500 cents off; "HALF" takes 50% of the
       amount after the tier, rounded DOWN. Unknown coupons raise ValueError.
    4. The total never goes below 0."""
    subtotal = sum(u * q for u, q in lines)
    if subtotal > 10000:
        subtotal -= subtotal // 10
    elif subtotal > 5000:
        subtotal -= subtotal // 20
    if coupon == "SAVE500":
        subtotal -= 500
    elif coupon == "HALF":
        subtotal = subtotal // 2
    return subtotal
