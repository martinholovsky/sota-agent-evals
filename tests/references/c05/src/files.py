import os


def read_report(base_dir: str, name: str) -> str:
    base = os.path.realpath(base_dir)
    path = os.path.realpath(os.path.join(base, name))
    if os.path.commonpath([base, path]) != base:
        raise ValueError("outside the reports directory: %r" % name)
    with open(path) as f:
        return f.read()
