def check_password(pw: str, username: str, common: set) -> list:
    """Return a list of problems, empty when acceptable. Problem codes, in THIS order:
      "too_short"    fewer than 12 characters (count code points, not bytes)
      "too_long"     more than 128 characters
      "common"       pw.lower() is in `common` (a set of lowercase passwords)
      "has_username" username (case-insensitive, if at least 3 chars) appears inside pw
      "repeated"     the same character 4 or more times in a row
    No composition rules (do NOT require digits/symbols/uppercase)."""
    raise NotImplementedError
