import re


def wrap(text: str, width: int) -> str:
    if width < 1:
        raise ValueError(width)
    paras = [p.split() for p in re.split(r"\n\s*\n", text)]
    out = []
    for words in paras:
        if not words:
            continue
        chunks = []
        for w in words:
            chunks += [w[i:i + width] for i in range(0, len(w), width)] if len(w) > width else [w]
        lines, cur = [], ""
        for w in chunks:
            if cur and len(cur) + 1 + len(w) <= width:
                cur += " " + w
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        out.append("\n".join(lines))
    return "\n\n".join(out)
