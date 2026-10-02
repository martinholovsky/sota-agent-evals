def parse_config(text: str) -> dict:
    out, section = {}, ""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        n = i + 1
        line = lines[i]
        while line.endswith("\\") and i + 1 < len(lines):
            i += 1
            line = line[:-1].rstrip() + " " + lines[i].strip()
        i += 1
        s = line.strip()
        if not s or s[0] in "#;":
            continue
        if s.startswith("["):
            if not s.endswith("]"):
                raise ValueError("line %d: bad section" % n)
            section = s[1:-1]
            out.setdefault(section, {})
            continue
        if "=" not in s:
            raise ValueError("line %d: expected key = value" % n)
        k, v = s.split("=", 1)
        out.setdefault(section, {})[k.strip()] = v.strip()
    return out
