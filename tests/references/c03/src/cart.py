from src.pricing import total_price


def cart_total(lines):
    return sum(total_price(q, p, d) for q, p, d in lines)
