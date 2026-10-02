def diff(old: dict, new: dict, path: str = "") -> list:
    """Return the operations turning `old` into `new`, as dicts:
        {"op": "add", "path": p, "value": v}, {"op": "remove", "path": p},
        {"op": "replace", "path": p, "value": v}
    - Paths are "/"-joined keys from the root ("/a/b"); `path` is the prefix.
    - Keys are visited in sorted order; within a key, recurse when BOTH values are dicts.
    - A value that changes type, or any non-dict value that differs, is a replace.
    - Lists are compared as whole values (no element diff).
    - 1 and True are DIFFERENT values (and 1 vs 1.0 too): compare with type.
    - Equal inputs give []."""
    raise NotImplementedError
