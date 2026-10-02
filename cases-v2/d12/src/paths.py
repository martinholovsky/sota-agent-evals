def safe_join(root: str, url_path: str) -> str:
    """Map a URL path to a file path under `root` (an absolute directory path), purely
    lexically (do not touch the filesystem).
    - Percent-decode url_path first ("%2e%2e" is "..").
    - Reject (ValueError) a decoded path containing a NUL byte or a backslash.
    - Normalise "." and ".." segments and repeated slashes; if the result would escape
      `root`, raise ValueError.
    - A path that resolves to root itself returns root; otherwise root + "/" + the
      normalised relative path. Never return a trailing slash."""
    raise NotImplementedError
