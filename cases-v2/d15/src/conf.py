def parse_config(text: str) -> dict:
    """Parse an INI-like format into {section: {key: value}}.
    - "[name]" starts a section; keys before any section go in section "".
    - "key = value": key and value are stripped; the FIRST "=" splits.
    - Lines whose first non-space character is "#" or ";" are comments; blank lines skip.
    - A line ending in a backslash continues on the next line: the backslash is dropped and
      the next line (stripped) is appended with one space.
    - A repeated key in the same section: the LAST value wins.
    - Section and key names are case-sensitive.
    - Any other line (e.g. no "=", or "[" without "]") raises ValueError naming the
      1-based line number ("line 3")."""
    raise NotImplementedError
