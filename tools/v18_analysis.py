#!/usr/bin/env python3
"""v18 analysis, as PRE-REGISTRATION-v18.md fixes it. Written before any v18 main-run row existed.

Usage: v18_analysis.py <results-dir> <sota-root>    (prints the table; exit 0)

Primary: rule tests passed per arm, and task-level paired counts (B passed more rule tests than A,
fewer, equal); one-sided sign test over discordant tasks. Harm guard 1: spec-test pass counts.
(Harm guard 2, never-mentioned, needs the 2026-11-01 rubric's judges: a separate step.)
Secondary: gate fired per arm. A (shadow) by replaying the frozen root's `spec_reason_sentences` on
the final text (D1). B by Claude Code's `stop-hook-error` notification in the trace (D2), which is
how it reports a deliberate `decision: block`.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

A, B = "installed+table+code+gate-shadow", "installed+table+code+gate"


def main(results: Path, root: Path) -> int:
    sp = importlib.util.spec_from_file_location("gate", root / "scripts" / "completion-gate-hook.py")
    gate = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(gate)
    rows = [json.loads(l) for l in (results / "runs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    by = {(r["case"], r["arm"]): r for r in rows}
    cases = sorted({r["case"] for r in rows})

    def trace(case, arm):
        f = results / "traces" / ("%s__%s__0.json" % (case, arm.replace("+", "_")))
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

    tot = {A: [0, 0], B: [0, 0]}
    spec = {A: 0, B: 0}
    cost = {A: 0.0, B: 0.0}
    fired = {A: 0, B: 0}
    up = down = same = 0
    missing = []
    print("case   A rules  B rules  A spec B spec  A would-block  B blocked")
    for c in cases:
        if (c, A) not in by or (c, B) not in by:
            missing.append(c)
            continue
        ra, rb = by[(c, A)], by[(c, B)]
        pa, ta = ra["hidden"]["rules"]["passed"], ra["hidden"]["rules"]["total"]
        pb, tb = rb["hidden"]["rules"]["passed"], rb["hidden"]["rules"]["total"]
        for arm, p, t, r in ((A, pa, ta, ra), (B, pb, tb, rb)):
            tot[arm][0] += p
            tot[arm][1] += t
            spec[arm] += bool(r["hidden"].get("spec_ok"))
            cost[arm] += (r.get("result") or {}).get("total_cost_usd") or 0.0
        wa = bool(gate.spec_reason_sentences(trace(c, A).get("final_text") or ""))
        bb = any("stop-hook-error" in (s.get("data") or "") for s in trace(c, B).get("system") or [])
        fired[A] += wa
        fired[B] += bb
        up += pb > pa
        down += pb < pa
        same += pb == pa
        print("%-6s %3d/%-3d  %3d/%-3d  %-6s %-6s %-14s %s" % (c, pa, ta, pb, tb, ra["hidden"].get("spec_ok"),
                                                         rb["hidden"].get("spec_ok"), wa, bb))
    n = up + down
    p_one = sum(math.comb(n, k) for k in range(up, n + 1)) / 2 ** n if n else 1.0
    print("\nrule tests: A %d/%d, B %d/%d" % (tot[A][0], tot[A][1], tot[B][0], tot[B][1]))
    print("tasks: B more %d, B fewer %d, equal %d; net %+d; one-sided sign test p = %.4f" % (up, down, same, up - down, p_one))
    print("spec ok: A %d, B %d (of %d)" % (spec[A], spec[B], len(cases) - len(missing)))
    print("gate: A would-block %d, B blocked %d" % (fired[A], fired[B]))
    print("cost (SDK estimate): A $%.2f, B $%.2f" % (cost[A], cost[B]))
    if missing:
        print("MISSING a pair (excluded from the paired counts): %s" % ", ".join(missing))
    net = up - down
    verdict = ("SUPPORTED" if net >= 3 and p_one < 0.05 else "NULL" if net <= 0 else "INCONCLUSIVE")
    if spec[A] - spec[B] > 1:
        verdict = "HARM (spec)"
    print("primary, before harm guard 2: %s" % verdict)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stderr.write("usage: v18_analysis.py <results-dir> <sota-root>\n")
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
