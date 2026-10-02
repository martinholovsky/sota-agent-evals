from collections import OrderedDict


def memo(maxsize: int):
    if maxsize < 1:
        raise ValueError("maxsize must be >= 1")

    def deco(fn):
        cache = OrderedDict()

        def wrapper(*args):
            if args in cache:
                cache.move_to_end(args)
                return cache[args]
            v = fn(*args)
            cache[args] = v
            if len(cache) > maxsize:
                cache.popitem(last=False)
            return v
        wrapper.cache_len = lambda: len(cache)
        return wrapper
    return deco
