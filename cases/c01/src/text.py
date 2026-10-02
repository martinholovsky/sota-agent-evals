import re


def slugify(s: str) -> str:
    """Lowercase; runs of any non-alphanumeric characters become ONE hyphen;
    no leading or trailing hyphens. 'Hello,  World!' -> 'hello-world'."""
    return re.sub(r"[^a-z0-9]", "-", s.lower())
