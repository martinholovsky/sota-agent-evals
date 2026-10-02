def parse_range(header: str, size: int) -> list:
    """Parse an HTTP Range header for a resource of `size` bytes (size >= 1).
    Return a list of (start, end) INCLUSIVE byte positions, in the order given.
    - The unit must be "bytes=" exactly; otherwise ValueError.
    - Ranges are comma-separated; spaces around them are allowed.
    - "a-b": bytes a..b; b past the end is clamped to size-1. a > b is a ValueError.
    - "a-": from a to the end.
    - "-n": the LAST n bytes (n > 0); n larger than size means the whole resource.
    - A range whose start is >= size is unsatisfiable: it is skipped. If NO range is
      satisfiable, raise ValueError.
    - Anything else (non-digits, "-", empty) is a ValueError."""
    raise NotImplementedError
