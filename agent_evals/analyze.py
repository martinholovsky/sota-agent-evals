"""The pre-registered analysis (PRE-REGISTRATION.md), written before any measurement result.

    python -m agent_evals.analyze results/<date>/runs.jsonl

Per arm: rates of hidden_pass and unverified_done with exclusions counted, not hidden.
Per hypothesis: the paired per-case difference and a 95% bootstrap CI that resamples CASES
(the unit), not runs — runs of one case are correlated, and resampling them would shrink the CI.
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict

HYPOTHESES_V2 = [  # PRE-REGISTRATION-v2.md
    ("H1a hook vs bare: fewer broken 'done'", "shipped_broken", "hook", "bare", -1),
    ("H1b library+hook vs library: fewer broken 'done'", "shipped_broken", "library+hook", "library", -1),
    ("H2 library vs bare: hidden_pass", "hidden_pass", "library", "bare", +1),
    ("H3 hook vs bare: hidden_pass", "hidden_pass", "hook", "bare", +1),
]

HYPOTHESES = [  # v1 (PRE-REGISTRATION.md) — kept unchanged so the v1 analysis reproduces
    # (name, metric, treatment, control, direction: +1 = treatment should be higher)
    ("H1a hook vs bare", "unverified_done", "hook", "bare", -1),
    ("H1b library+hook vs library", "unverified_done", "library+hook", "library", -1),
    ("H2 library vs bare", "hidden_pass", "library", "bare", +1),
    ("H3 hook vs bare (non-inferiority)", "hidden_pass", "hook", "bare", 0),
]


def value(row, metric):
    if metric == "shipped_broken":
        v = row.get("shipped_broken")
        return None if v is None else float(v)
    if metric == "hidden_pass":
        ok = (row.get("hidden") or {}).get("ok")
        return None if ok is None else float(ok)
    v = row.get("unverified_done")
    return None if v is None else float(v)


def excluded(row):
    if row.get("error"):
        return "error"
    c = row.get("contamination") or {}
    if c.get("contaminated") or c.get("treatment_present") is False:
        return "contaminated"
    if "hook_ledger" in row and row["hook_ledger"] != ("hook" in row["arm"]):
        return "hook-treatment-mismatch"     # hook arm where it never ran, or a ledger it shouldn't have
    return None


def per_case(rows, metric):
    """{arm: {case: mean over samples}} over non-excluded rows with a defined value."""
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if excluded(r):
            continue
        v = value(r, metric)
        if v is not None:
            acc[r["arm"]][r["case"]].append(v)
    return {a: {c: sum(v) / len(v) for c, v in cs.items()} for a, cs in acc.items()}


def bootstrap_diff(t: dict, c: dict, iters=10000, seed=0):
    cases = sorted(set(t) & set(c))           # paired: only cases present in both arms
    if not cases:
        return None
    diffs = [t[k] - c[k] for k in cases]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(iters))
    return {"n_cases": len(cases), "diff": sum(diffs) / len(diffs),
            "ci95": (means[int(0.025 * iters)], means[int(0.975 * iters) - 1])}


def analyze(rows, hypotheses=None):
    hypotheses = hypotheses or HYPOTHESES
    out = {"rows": len(rows), "excluded": defaultdict(int), "arms": {}, "hypotheses": []}
    for r in rows:
        why = excluded(r)
        if why:
            out["excluded"][why + ":" + r["arm"]] += 1
    for metric in ("hidden_pass", "unverified_done", "shipped_broken"):
        for arm, cs in per_case(rows, metric).items():
            out["arms"].setdefault(arm, {})[metric] = round(sum(cs.values()) / len(cs), 3) if cs else None
    for name, metric, t, c, direction in hypotheses:
        pc = per_case(rows, metric)
        b = bootstrap_diff(pc.get(t, {}), pc.get(c, {}))
        if b is None:
            out["hypotheses"].append({"name": name, "verdict": "NO DATA"})
            continue
        lo, hi = b["ci95"]
        if direction > 0:
            verdict = "SUPPORTED" if lo > 0 else "NOT SUPPORTED"
        elif direction < 0:
            verdict = "SUPPORTED" if hi < 0 else "NOT SUPPORTED"
        else:   # non-inferiority: the CI's lower bound must not fall below -0.10
            verdict = "SUPPORTED" if lo > -0.10 else "NOT SUPPORTED"
        out["hypotheses"].append(dict(b, name=name, metric=metric, verdict=verdict))
    out["excluded"] = dict(out["excluded"])
    return out


def main(argv=None):
    args = argv or sys.argv[1:]
    hyps = HYPOTHESES_V2 if "--v2" in args else HYPOTHESES
    path = [a for a in args if a != "--v2"][0]
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    print(json.dumps(analyze(rows, hyps), indent=2, default=str))


if __name__ == "__main__":
    main()
