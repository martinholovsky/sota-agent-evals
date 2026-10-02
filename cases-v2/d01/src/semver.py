def compare(a: str, b: str) -> int:
    """Compare two Semantic Versioning 2.0.0 strings; return -1, 0 or 1.
    - Format MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]; MAJOR/MINOR/PATCH are non-negative
      integers without leading zeros ("01" is invalid). Invalid input raises ValueError.
    - Compare MAJOR, MINOR, PATCH numerically, in that order.
    - A version WITH a prerelease has LOWER precedence than the same version without one.
    - Prerelease identifiers (dot-separated) compare left to right: numeric identifiers
      numerically; alphanumeric ones lexically in ASCII order; numeric < alphanumeric; if all
      shared identifiers are equal, the one with MORE identifiers is greater.
    - Build metadata (after "+") is IGNORED for precedence."""
    raise NotImplementedError
