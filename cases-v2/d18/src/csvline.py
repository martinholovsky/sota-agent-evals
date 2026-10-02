def parse_line(line: str, sep: str = ",") -> list:
    """Split one CSV record (RFC 4180 style) into fields.
    - Fields are separated by `sep`.
    - A field may be quoted with double quotes; inside quotes `sep` is literal and a
      doubled quote "" is one quote character.
    - Unquoted fields are taken verbatim (no stripping).
    - An empty line is one empty field: [""]. A trailing separator means a final empty field.
    - A quote that is not closed, or characters after a closing quote before the next
      separator, raise ValueError."""
    raise NotImplementedError
