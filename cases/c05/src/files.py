import os


def read_report(base_dir: str, name: str) -> str:
    """Return the text of the report `name` inside base_dir."""
    with open(os.path.join(base_dir, name)) as f:
        return f.read()
