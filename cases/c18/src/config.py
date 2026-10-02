def deep_merge(base: dict, override: dict) -> dict:
    """Return a NEW dict: keys from both; where both values are dicts, merge them
    recursively; otherwise the override wins. Neither input is modified, and the result
    shares no nested dict with either input."""
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base
