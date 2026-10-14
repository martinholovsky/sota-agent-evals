#!/usr/bin/env python3
"""Where v14's extra cost goes. No model calls; reads the two runs.jsonl files and the kept
transcripts. Usage (from the repo root):

    python3 reports/2026-10-13-v14/tools/cost.py results/cal-v5-2026-10-13 results/v14-2026-10-13

1. Fits per-token prices (output, cache read, cache write) to every run's SDK cost by least
   squares, prints the residual, and splits each arm's cost by token type.
2. Counts Read calls on rules files and the characters they returned, and the share of those
   characters from a file the case's rules.json cites.
3. Counts which hook trigger named which rules file (treatment transcripts only).
"""
import glob
import json
import os
import re
import sys
from collections import Counter

ARMS = {"control": "reports/2026-10-13-cases-v5-calibration/runs.jsonl",
        "shipped default": "reports/2026-10-13-v14/runs.jsonl"}
TOKENS = ("output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
MARK = "SOTA: the code you just wrote in"


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


def solve(a, b):
    m = [row + [v] for row, v in zip(a, b)]
    n = len(m)
    for i in range(n):
        piv = m[i][i]
        m[i] = [v / piv for v in m[i]]
        for k in range(n):
            if k != i:
                f = m[k][i]
                m[k] = [x - f * y for x, y in zip(m[k], m[i])]
    return [m[i][n] for i in range(n)]


def prices(rows):
    x = [[r["result"]["usage"][k] for k in TOKENS] for r in rows]
    y = [r["result"]["total_cost_usd"] for r in rows]
    a = [[sum(r[i] * r[j] for r in x) for j in range(3)] for i in range(3)]
    b = [sum(r[i] * v for r, v in zip(x, y)) for i in range(3)]
    p = solve(a, b)
    resid = max(abs(sum(u * q for u, q in zip(r, p)) - v) for r, v in zip(x, y))
    return p, resid


def cited_files():
    out = {}
    for rj in glob.glob("cases-v5/tasks/*/rules.json"):
        case = rj.split("/")[2]
        out[case] = {s.split("skills/")[-1] for s in strings(json.load(open(rj)))
                     if "/rules/" in s and s.endswith(".md")}
    return out


def transcripts(root, cited):
    reads, named = [], Counter()
    for tdir in sorted(glob.glob(os.path.join(root, "transcripts", "*"))):
        case = os.path.basename(tdir).split("__")[0]
        ids, seen = {}, set()
        for f in glob.glob(tdir + "/**/*.jsonl", recursive=True):
            for line in open(f):
                if MARK in line:
                    for what, path in re.findall(r"- ([^\n\\]+?)\. Its rules: ([^ \\]+)", line):
                        key = (what, path)
                        if key not in seen:
                            seen.add(key)
                            named[(what, path.split("skills/")[-1])] += 1
                if '"tool_use"' not in line and '"tool_result"' not in line:
                    continue
                msg = json.loads(line).get("message") or {}
                content = msg.get("content") if isinstance(msg.get("content"), list) else []
                for c in content:
                    if (c.get("type") == "tool_use" and c.get("name") == "Read"
                            and "/rules/" in c["input"].get("file_path", "")):
                        ids[c["id"]] = c["input"]["file_path"]
                    if c.get("type") == "tool_result" and c.get("tool_use_id") in ids:
                        rel = ids[c["tool_use_id"]].split("skills/")[-1]
                        size = len("".join(strings(c.get("content"))))
                        reads.append((case, rel, size, rel in cited.get(case, set())))
    return reads, named


def main():
    roots = dict(zip(ARMS, sys.argv[1:3]))
    rows = {arm: [json.loads(l) for l in open(p)] for arm, p in ARMS.items()}
    p, resid = prices(rows["control"] + rows["shipped default"])
    print("fitted $/Mtok output, cache read, cache write: %s; max residual $%.6f"
          % ([round(v * 1e6, 3) for v in p], resid))
    cited = cited_files()
    print("cases with a cited rules file: %d of %d" % (sum(1 for v in cited.values() if v), len(cited)))
    for arm, rs in rows.items():
        parts = [sum(r["result"]["usage"][k] * q for r in rs) for k, q in zip(TOKENS, p)]
        turns = sum(r["result"]["num_turns"] for r in rs)
        print("\n%s: runs %d, turns %d, cost $%.2f = output $%.2f + cache read $%.2f + cache write $%.2f"
              % (arm, len(rs), turns, sum(parts), *parts))
        reads, named = transcripts(roots[arm], cited)
        total = sum(r[2] for r in reads)
        cit = sum(r[2] for r in reads if r[3])
        print("  rules-file Reads %d (harness depth.rules_read %d), chars %s, from a cited file %.0f%%"
              % (len(reads), sum(r["depth"].get("rules_read", 0) for r in rs), format(total, ","),
                 100 * cit / max(total, 1)))
        print("  most-read:", Counter(r[1] for r in reads).most_common(4))
        if named:
            print("  hook namings (trigger, file): %d" % sum(named.values()))
            for (what, path), n in named.most_common(4):
                print("    %2d  %s -> %s" % (n, what[:50], path))


if __name__ == "__main__":
    main()
