from urllib.parse import unquote


def safe_join(root: str, url_path: str) -> str:
    p = unquote(url_path)
    if "\x00" in p or "\\" in p:
        raise ValueError("bad character")
    parts = []
    for seg in p.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not parts:
                raise ValueError("escapes root")
            parts.pop()
        else:
            parts.append(seg)
    root = root.rstrip("/") or "/"
    return root if not parts else root.rstrip("/") + "/" + "/".join(parts)
