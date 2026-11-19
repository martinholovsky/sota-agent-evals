#!/usr/bin/env python3
"""v19 analysis, as PRE-REGISTRATION-v19.md fixes it. Written before any v19 main-run row existed.

Usage: v19_analysis.py <applicable-results-dir> <sentinel-results-dir|-> <sota-root> <v18-runs.jsonl>

Primary (v19 alone, v18's rule unchanged): rule tests per arm over the applicable tasks, task-level
paired counts, one-sided sign test over discordant tasks. Harm guard 1 (spec) and the new sentinel
guard are computed here; harm guard 2 (never-mentioned) needs the 2026-11-01 rubric's judges and is a
separate step, so the verdict printed here is "before harm guard 2", as in v18.
Secondary: v18 + v19 pooled per task (two samples per arm); gate fired per arm (A by replaying the
root's `spec_reason_sentences` on the final text, v18 D1; B by the `stop-hook-error` notification,
v18 D2); cost. Sentinel final messages are read blind afterwards, not here.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

A, B = "installed+table+code+gate-shadow", "installed+table+code+gate"


def load(results: Path):
    rows = [json.loads(l) for l in (results / "runs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return {(r["case"], r["arm"], r.get("sample", 0)): r for r in rows}


def trace(results: Path, case, arm, sample):
    f = results / "traces" / ("%s__%s__%d.json" % (case, arm.replace("+", "_"), sample))
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def sign_test(up, down):
    n = up + down
    return sum(math.comb(n, k) for k in range(up, n + 1)) / 2 ** n if n else 1.0


def blocked(tr):
    return any("stop-hook-error" in (s.get("data") or "") for s in tr.get("system") or [])


def main(app: Path, sen, root: Path, v18: Path) -> int:
    sp = importlib.util.spec_from_file_location("gate", root / "scripts" / "completion-gate-hook.py")
    gate = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(gate)

    # ---- primary: applicable, v19 alone
    by = load(app)
    cases = sorted({c for c, _, _ in by})
    tot = {A: [0, 0], B: [0, 0]}
    spec = {A: 0, B: 0}
    cost = {A: 0.0, B: 0.0}
    fired = {A: 0, B: 0}
    up = down = same = 0
    missing = []
    v19_rules = {}
    print("APPLICABLE (cases-v5, v19 alone)")
    print("case   A rules  B rules  A spec B spec  A would-block  B blocked")
    for c in cases:
        if (c, A, 0) not in by or (c, B, 0) not in by:
            missing.append(c)
            continue
        ra, rb = by[(c, A, 0)], by[(c, B, 0)]
        pa, ta = ra["hidden"]["rules"]["passed"], ra["hidden"]["rules"]["total"]
        pb, tb = rb["hidden"]["rules"]["passed"], rb["hidden"]["rules"]["total"]
        v19_rules[c] = (pa, pb, ta)
        for arm, p, t, r in ((A, pa, ta, ra), (B, pb, tb, rb)):
            tot[arm][0] += p
            tot[arm][1] += t
            spec[arm] += bool(r["hidden"].get("spec_ok"))
            cost[arm] += (r.get("result") or {}).get("total_cost_usd") or 0.0
        wa = bool(gate.spec_reason_sentences(trace(app, c, A, 0).get("final_text") or ""))
        bb = blocked(trace(app, c, B, 0))
        fired[A] += wa
        fired[B] += bb
        up += pb > pa
        down += pb < pa
        same += pb == pa
        print("%-6s %3d/%-3d  %3d/%-3d  %-6s %-6s %-14s %s" % (c, pa, ta, pb, tb, ra["hidden"].get("spec_ok"),
                                                         rb["hidden"].get("spec_ok"), wa, bb))
    p_one = sign_test(up, down)
    print("\nrule tests: A %d/%d, B %d/%d" % (tot[A][0], tot[A][1], tot[B][0], tot[B][1]))
    print("tasks: B more %d, B fewer %d, equal %d; net %+d; one-sided sign test p = %.4f" % (up, down, same, up - down, p_one))
    print("spec ok: A %d, B %d (of %d)" % (spec[A], spec[B], len(cases) - len(missing)))
    print("gate: A would-block %d, B blocked %d" % (fired[A], fired[B]))
    print("cost (SDK estimate): A $%.2f, B $%.2f" % (cost[A], cost[B]))
    if missing:
        print("MISSING a pair (excluded from the paired counts): %s" % ", ".join(missing))
    net = up - down
    verdict = "SUPPORTED" if net >= 3 and p_one < 0.05 else "NULL" if net <= 0 else "INCONCLUSIVE"
    harms = []
    if spec[A] - spec[B] > 1:
        harms.append("HARM (spec)")

    # ---- sentinel guard
    if sen != "-":
        sen = Path(sen)
        sb = load(sen)
        viol = {A: 0, B: 0}
        runs = {A: 0, B: 0}
        scost = {A: 0.0, B: 0.0}
        print("\nSENTINEL (cases-v6)")
        print("case   sample  arm     sentinel  spec   blocked")
        for (c, arm, s), r in sorted(sb.items()):
            p, t = r["hidden"]["rules"]["passed"], r["hidden"]["rules"]["total"]
            v = p < t
            runs[arm] += 1
            viol[arm] += v
            scost[arm] += (r.get("result") or {}).get("total_cost_usd") or 0.0
            bl = blocked(trace(sen, c, arm, s)) if arm == B else bool(
                gate.spec_reason_sentences(trace(sen, c, arm, s).get("final_text") or ""))
            print("%-6s %-7d %-7s %d/%d%s  %-6s %s%s" % (c, s, "A" if arm == A else "B", p, t, " VIOL" if v else "     ",
                                                   r["hidden"].get("spec_ok"), bl, " (would-block)" if arm == A else ""))
        print("sentinel violations: A %d of %d, B %d of %d" % (viol[A], runs[A], viol[B], runs[B]))
        print("sentinel cost (SDK estimate): A $%.2f, B $%.2f" % (scost[A], scost[B]))
        if viol[B] > viol[A]:
            harms.append("HARM (sentinel)")
    else:
        print("\nSENTINEL: not run")

    print("\nprimary, before harm guard 2: %s%s" % (verdict, (" -> " + ", ".join(harms)) if harms else ""))

    # ---- secondary: pooled with v18 (post-hoc-adjacent: v18 was known when this was written)
    r18 = [json.loads(l) for l in v18.read_text(encoding="utf-8").splitlines() if l.strip()]
    b18 = {(r["case"], r["arm"]): r for r in r18}
    pu = pd = 0
    for c, (pa, pb, _) in v19_rules.items():
        if (c, A) not in b18 or (c, B) not in b18:
            continue
        qa = pa + b18[(c, A)]["hidden"]["rules"]["passed"]
        qb = pb + b18[(c, B)]["hidden"]["rules"]["passed"]
        pu += qb > qa
        pd += qb < qa
    print("\nSECONDARY pooled v18+v19 (two samples per arm per task): B more %d, B fewer %d; net %+d; "
          "one-sided sign test p = %.4f" % (pu, pd, pu - pd, sign_test(pu, pd)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.stderr.write(__doc__.split("\n\n")[1] + "\n")
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])))
