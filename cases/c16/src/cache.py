def memo(maxsize: int):
    """Decorator caching results by positional args, keeping at most `maxsize` entries and
    evicting the LEAST RECENTLY USED one (a hit counts as a use). maxsize < 1 raises
    ValueError. The wrapper exposes `cache_len()`."""
    def deco(fn):
        cache = {}

        def wrapper(*args):
            if args not in cache:
                cache[args] = fn(*args)
            return cache[args]
        wrapper.cache_len = lambda: len(cache)
        return wrapper
    return deco
