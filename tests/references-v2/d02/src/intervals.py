def merge(intervals: list) -> list:
    for s, e in intervals:
        if s > e:
            raise ValueError((s, e))
    out = []
    for s, e in sorted((s, e) for s, e in intervals if s != e):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out
