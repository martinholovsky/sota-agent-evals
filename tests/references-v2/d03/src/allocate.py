from fractions import Fraction


def allocate(total_cents: int, ratios: list) -> list:
    if not ratios or any(r < 0 for r in ratios) or sum(ratios) <= 0:
        raise ValueError(ratios)
    sign, total = (-1 if total_cents < 0 else 1), abs(total_cents)
    fr = [Fraction(r).limit_denominator(10**9) for r in ratios]
    s = sum(fr)
    exact = [total * r / s for r in fr]
    base = [int(x) for x in exact]
    left = total - sum(base)
    order = sorted(range(len(fr)), key=lambda i: (-(exact[i] - base[i]), i))
    for i in order[:left]:
        base[i] += 1
    return [sign * b for b in base]
