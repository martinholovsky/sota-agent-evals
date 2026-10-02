def order_total(lines: list, coupon: str | None = None) -> int:
    subtotal = sum(u * q for u, q in lines)
    if subtotal >= 10000:
        amount = subtotal - subtotal * 10 // 100
    elif subtotal >= 5000:
        amount = subtotal - subtotal * 5 // 100
    else:
        amount = subtotal
    if coupon is None:
        pass
    elif coupon == "SAVE500":
        amount -= 500
    elif coupon == "HALF":
        amount -= amount // 2
    else:
        raise ValueError("unknown coupon %r" % coupon)
    return max(0, amount)
