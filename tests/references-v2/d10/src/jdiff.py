def _same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def diff(old: dict, new: dict, path: str = "") -> list:
    ops = []
    for k in sorted(set(old) | set(new)):
        p = path + "/" + str(k)
        if k not in new:
            ops.append({"op": "remove", "path": p})
        elif k not in old:
            ops.append({"op": "add", "path": p, "value": new[k]})
        elif isinstance(old[k], dict) and isinstance(new[k], dict):
            ops += diff(old[k], new[k], p)
        elif not _same(old[k], new[k]):
            ops.append({"op": "replace", "path": p, "value": new[k]})
    return ops
