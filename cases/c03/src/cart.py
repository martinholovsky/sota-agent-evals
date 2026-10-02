from src.pricing import calc


def cart_total(lines):
    return sum(calc(q, p, d) for q, p, d in lines)
