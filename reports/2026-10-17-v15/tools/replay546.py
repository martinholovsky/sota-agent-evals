#!/usr/bin/env python3
"""#546 offline replay: what v15's default arm would have paid if every rules-file Read had
returned only the sections the hook names, plus the preamble and the Audit checklist (which
the hook also asks for). No model calls; reads the runs.jsonl files and the kept transcripts.
Usage (from the repo root):

    python3 reports/2026-10-17-v15/tools/replay546.py results/v15-treatment-2026-10-17 \
        ~/Github/SOTA-skills 4a5fee40

1. Fits per-token prices to every v15 run's SDK cost by least squares (as v14's cost.py).
2. For each rules-file Read, finds the sections named for that file in the same transcript
   (hook messages; optionally the router's "What your code does" table at the commit) and
   the share of the file they hold. A file with no section named stays whole.
3. Prices the text: one cache write plus one cache read per later API call. Characters per
   token is NOT measured here; the result is printed for 3.0, 3.5 and 4.0.

What it cannot say: whether rule tests hold with less text, or whether agents would read
more (re-reads, follow-ups) once given only a section. Both make the saving an upper bound.
"""
import glob
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

REPORT = "reports/2026-10-17-v15"
TOKENS = ("output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
MARK = "SOTA: the code you just wrote in"
NAMED = re.compile(r"Its rules: \S+?/skills/(sota-\S+\.md) \(([^)]*)\)")


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


def prices(rows):
    x = [[r["result"]["usage"][k] for k in TOKENS] for r in rows]
    y = [r["result"]["total_cost_usd"] for r in rows]
    m = [[sum(a[i] * a[j] for a in x) for j in range(3)] + [sum(a[i] * v for a, v in zip(x, y))]
         for i in range(3)]
    for i in range(3):
        m[i] = [v / m[i][i] for v in m[i]]
        for k in range(3):
            if k != i:
                m[k] = [a - m[k][i] * b for a, b in zip(m[k], m[i])]
    p = [m[i][3] for i in range(3)]
    resid = max(abs(sum(u * q for u, q in zip(a, p)) - v) for a, v in zip(x, y))
    return p, resid


def nums(s):
    """Section numbers in '§1, §2 and §4' or '§1-§3'."""
    got = set()
    for a, b in re.findall(r"§(\d+)(?:\s*-\s*§?(\d+))?", s):
        got |= {str(n) for n in range(int(a), int(b or a) + 1)}
    return got


def git_show(repo, sha, path):
    return subprocess.run(["git", "-C", repo, "show", f"{sha}:skills/{path}"],
                          capture_output=True, text=True, check=True).stdout


def sections(text):
    """{label: chars}: '1', '2', ... for '## N.' (subsections fold in), 'pre', 'audit'."""
    out, cur = defaultdict(int), "pre"
    for line in text.splitlines(True):
        m = re.match(r"## (\d+)\.", line)
        if m:
            cur = m.group(1)
        elif line.startswith("## Audit checklist"):
            cur = "audit"
        elif line.startswith("## "):
            cur = "other:" + line.strip()
        out[cur] += len(line)
    return out


def router_table(repo, sha):
    """Sections the router table names per file. A row's 'When' cell counts only when the
    row links one file; each row names a file twice (label and link), so count links."""
    block = git_show(repo, sha, "sota/SKILL.md").split("## What your code does")[1].split("\n## ")[0]
    table = defaultdict(set)
    for row in block.splitlines():
        if not row.startswith("| ") or "](../" not in row:
            continue
        when, where = row.split("|")[1:3]
        for m in re.finditer(r"\(\.\./(sota-[^)]+\.md)\)([^;|]*)", where):
            table[m.group(1)] |= nums(m.group(2)) | (nums(when) if where.count("](../") == 1 else set())
    return table


def hook_named(lines):
    named = defaultdict(set)
    for o in lines:
        for s in strings(o):
            if MARK in s and s.lstrip().startswith("{"):   # hook output is JSON inside JSON
                try:
                    s = "\n".join(strings(json.loads(s)))
                except ValueError:
                    pass
            if MARK in s:
                for path, note in NAMED.findall(s):
                    named[path] |= nums(note)
    return named


def reads(root):
    """(case, file, chars returned, API calls after it, sections hook-named) per rules Read."""
    out = []
    for tdir in sorted(glob.glob(os.path.join(root, "transcripts", "*"))):
        case = os.path.basename(tdir).split("__")[0]
        for f in glob.glob(tdir + "/**/*.jsonl", recursive=True):
            lines = [json.loads(line) for line in open(f)]
            named = hook_named(lines)
            calls, seen = [], set()
            for i, o in enumerate(lines):
                mid = (o.get("message") or {}).get("id")
                if o.get("type") == "assistant" and mid not in seen:
                    seen.add(mid)
                    calls.append(i)
            ids = {}
            for i, o in enumerate(lines):
                content = (o.get("message") or {}).get("content")
                for c in content if isinstance(content, list) else []:
                    if (c.get("type") == "tool_use" and c.get("name") == "Read"
                            and "/rules/" in c["input"].get("file_path", "")):
                        ids[c["id"]] = c["input"]["file_path"].split("/skills/")[-1]
                    if c.get("type") == "tool_result" and c.get("tool_use_id") in ids:
                        rel = ids[c["tool_use_id"]]
                        size = len("".join(strings(c.get("content"))))
                        out.append((case, rel, size, sum(1 for j in calls if j > i), named[rel]))
    return out


def main():
    root, repo, sha = sys.argv[1:4]
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha):   # reaches git argv; no '-' option
        sys.exit("commit must be a hex sha, got %r" % sha)
    runs = {a: [json.loads(line) for line in open(f"{REPORT}/runs-{a}-pressure.jsonl")]
            for a in ("control", "treatment")}
    (p_out, p_read, p_write), resid = prices(runs["control"] + runs["treatment"])
    print("fitted $/Mtok output %.3f, cache read %.3f, cache write %.3f; max residual $%.6f"
          % (p_out * 1e6, p_read * 1e6, p_write * 1e6, resid))
    cost = {a: sum(r["result"]["total_cost_usd"] for r in rs) for a, rs in runs.items()}
    gap = cost["treatment"] - cost["control"]
    print("actual: control $%.2f, default $%.2f, gap $%.2f (+%.0f%%)"
          % (cost["control"], cost["treatment"], gap, 100 * gap / cost["control"]))

    secs = {}

    def kept(rel, named):
        if rel not in secs:
            secs[rel] = sections(git_show(repo, sha, rel))
        s = secs[rel]
        if not named:
            return 1.0, 0.0
        tot = sum(s.values())
        keep = sum(v for k, v in s.items() if k in named or k in ("pre", "audit"))
        return keep / tot, s.get("audit", 0) / tot

    rs = reads(root)
    table = router_table(repo, sha)
    print("rules-file Reads %d (harness depth.rules_read %d)"
          % (len(rs), sum(r["depth"].get("rules_read", 0) for r in runs["treatment"])))
    full_chars = sum(r[2] for r in rs)
    full_turns = sum(r[2] * r[3] for r in rs)
    for label, extra in (("hook only", {}), ("hook + router table", table)):
        k = [kept(rel, named | extra.get(rel, set()))[0] for _, rel, _, _, named in rs]
        kept_chars = sum(r[2] * f for r, f in zip(rs, k))
        saved_turns = sum(r[2] * r[3] * (1 - f) for r, f in zip(rs, k))
        print("\nsections named by %s: chars %s -> kept %s (%.0f%%)"
              % (label, format(full_chars, ","), format(round(kept_chars), ","), 100 * kept_chars / full_chars))
        for cpt in (3.0, 3.5, 4.0):
            text = (full_turns * p_read + full_chars * p_write) / cpt
            saved = (saved_turns * p_read + (full_chars - kept_chars) * p_write) / cpt
            print("  @%.1f chars/token: rules text $%.2f of the $%.2f gap; saves $%.2f ($%.3f/run)"
                  " -> default $%.2f (+%.0f%% vs control)"
                  % (cpt, text, gap, saved, saved / len(runs["treatment"]), cost["treatment"] - saved,
                     100 * (gap - saved) / cost["control"]))

    by = defaultdict(lambda: [0, 0, 0.0, 0.0])
    for _, rel, size, _, named in rs:
        f, audit = kept(rel, named)
        e = by[rel]
        e[0] += 1
        e[1] += size
        e[2] += size * f
        e[3] += size * audit
    print("\nfile (hook only): reads, chars read, kept, of which Audit checklist")
    for rel, (n, c, k, a) in sorted(by.items(), key=lambda kv: -kv[1][2]):
        print("  %-60s %3d %9s %9s %9s" % (rel, n, format(c, ","), format(round(k), ","), format(round(a), ",")))


if __name__ == "__main__":
    main()
