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

HYPOTHESES_V4 = [  # PRE-REGISTRATION-v4.md
    ("H4 installed vs bare: hidden_pass", "hidden_pass", "installed", "bare", +1),
    ("H5 installed vs library: hidden_pass (the routing layer's own effect)", "hidden_pass", "installed", "library", +1),
]
# The manipulation check that v1-v3 lacked: an arm meant to apply the library must actually
# INVOKE it. Below this share of runs with >= 1 Skill call, the treatment did not happen and
# every hypothesis on that arm is reported as MANIPULATION FAILED, never as a null.
MANIPULATION_MIN = 0.5

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


def analyze(rows, hypotheses=None, manipulation_check=False):
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
    # skill-call rate per library arm: share of non-excluded runs with >= 1 SOTA Skill call
    calls = defaultdict(list)
    for r in rows:
        c = r.get("contamination") or {}
        if not excluded(r) and c.get("treatment_present"):
            calls[r["arm"]].append(1.0 if (c.get("skill_calls") or 0) > 0 else 0.0)
    out["skill_call_rate"] = {a: round(sum(v) / len(v), 3) for a, v in calls.items() if v}
    # v4 only: v1-v3 were pre-registered without it, and their frozen analyses are not rewritten.
    failed = {a for a, rate in out["skill_call_rate"].items()
              if manipulation_check and rate < MANIPULATION_MIN}
    for h in out["hypotheses"]:
        t = next((x[2] for x in hypotheses if x[0] == h["name"]), None)
        if t in failed:
            h["verdict"] = "MANIPULATION FAILED"
    return out


# v5 (PRE-REGISTRATION-v5.md): the SAME `installed` arm run twice at the same time, once per
# router. Primary = share of valid runs that Read >= 1 rules file. Frozen before any v5 run.
V5_MIN_DIFF, V5_NULL_MAX, V5_ALPHA = 0.20, 0.05, 0.05


def fisher_one_sided(c_pos: int, c_n: int, t_pos: int, t_n: int) -> float:
    """Fisher's exact test, one-sided: P(treatment positives >= observed | both margins)."""
    from math import comb
    k_all, n_all = c_pos + t_pos, c_n + t_n
    return sum(comb(t_n, k) * comb(c_n, k_all - k)
               for k in range(t_pos, min(t_n, k_all) + 1)) / comb(n_all, k_all)


def _rate(rows, pred):
    return {"k": sum(1 for r in rows if pred(r)), "n": len(rows),
            "rate": round(sum(1 for r in rows if pred(r)) / len(rows), 3) if rows else None}


def analyze_v5(control: list, treatment: list) -> dict:
    out = {"arms": {}, "invalid": []}
    shas = {}
    for label, rows in (("control", control), ("treatment", treatment)):
        s = {r.get("router_sha") for r in rows}
        if len(s) != 1 or None in s:
            out["invalid"].append("%s file mixes routers or lacks router_sha: %s" % (label, sorted(map(str, s))))
        shas[label] = next(iter(s)) if len(s) == 1 else None
        excl = defaultdict(int)
        for r in rows:
            why = excluded(r) or (None if r["arm"] == "installed" else "wrong-arm")
            if why:
                excl[why] += 1
        valid = [r for r in rows if r["arm"] == "installed" and not excluded(r)]
        costs = [(r.get("result") or {}).get("total_cost_usd") or 0.0 for r in valid]
        turns = [(r.get("result") or {}).get("num_turns") or 0 for r in valid]
        hp = [value(r, "hidden_pass") for r in valid if value(r, "hidden_pass") is not None]
        out["arms"][label] = {
            "router_sha": shas[label], "rows": len(rows), "excluded": dict(excl),
            "excluded_share": round(sum(excl.values()) / len(rows), 3) if rows else None,
            "skill_call_rate": _rate(valid, lambda r: ((r.get("contamination") or {}).get("skill_calls") or 0) > 0),
            "rules_read": _rate(valid, lambda r: (r.get("depth") or {}).get("rules_read", 0) > 0),
            "rules_named": _rate(valid, lambda r: (r.get("depth") or {}).get("rules_named", 0) > 0),
            "further_skill": _rate(valid, lambda r: bool((r.get("depth") or {}).get("further_skill"))),
            "past_router": _rate(valid, lambda r: bool((r.get("depth") or {}).get("past_router"))),
            "hidden_pass": round(sum(hp) / len(hp), 3) if hp else None,
            "mean_cost_usd": round(sum(costs) / len(costs), 4) if costs else None,
            "mean_turns": round(sum(turns) / len(turns), 2) if turns else None,
        }
        if any("depth" not in r for r in valid):
            out["invalid"].append("%s has rows without a depth record" % label)
    if shas.get("control") and shas.get("control") == shas.get("treatment"):
        out["invalid"].append("both files ran the same router %s" % shas["control"])
    c, t = out["arms"]["control"], out["arms"]["treatment"]
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    if any((a["skill_call_rate"]["rate"] or 0) < MANIPULATION_MIN for a in (c, t)):
        out["verdict"] = "MANIPULATION FAILED"
        return out
    diff = t["rules_read"]["rate"] - c["rules_read"]["rate"]
    p = fisher_one_sided(c["rules_read"]["k"], c["rules_read"]["n"], t["rules_read"]["k"], t["rules_read"]["n"])
    out["primary"] = {"diff": round(diff, 3), "fisher_one_sided_p": round(p, 4)}
    out["verdict"] = ("SUPPORTED" if p < V5_ALPHA and diff >= V5_MIN_DIFF
                      else "NULL" if diff <= V5_NULL_MAX else "INCONCLUSIVE")
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in (c, t))
    return out


V6_ARMS = ("installed", "installed+depth")


def ctx(r: dict) -> dict:
    return r.get("context") or {}


def analyze_v6(rows: list) -> dict:
    """v6: one runs file, both arms interleaved against ONE checkout. Primary = share of valid runs
    whose tool results carried rules-file text (`context.rules_in_context`, from the CLI's own
    transcript). Validity: one router across the file; every valid row has a transcript; the
    treatment's hook text reached the model; both arms invoked a sota skill."""
    out = {"arms": {}, "invalid": []}
    shas = {r.get("router_sha") for r in rows}
    if len(shas) != 1 or None in shas:
        out["invalid"].append("file mixes routers or lacks router_sha: %s" % sorted(map(str, shas)))
    stray = sorted({r["arm"] for r in rows} - set(V6_ARMS))
    if stray:
        out["invalid"].append("unexpected arms %s" % stray)
    for label, arm in (("control", V6_ARMS[0]), ("treatment", V6_ARMS[1])):
        mine = [r for r in rows if r["arm"] == arm]
        excl = defaultdict(int)
        for r in mine:
            why = excluded(r)
            if why:
                excl[why] += 1
        valid = [r for r in mine if not excluded(r)]
        if any(not (r.get("context") or {}).get("transcripts") for r in valid):
            out["invalid"].append("%s has valid rows with no CLI transcript to score" % label)
        costs = [(r.get("result") or {}).get("total_cost_usd") or 0.0 for r in valid]
        turns = [(r.get("result") or {}).get("num_turns") or 0 for r in valid]
        hp = [value(r, "hidden_pass") for r in valid if value(r, "hidden_pass") is not None]
        out["arms"][label] = {
            "arm": arm, "rows": len(mine), "excluded": dict(excl),
            "excluded_share": round(sum(excl.values()) / len(mine), 3) if mine else None,
            "skill_call_rate": _rate(valid, lambda r: ((r.get("contamination") or {}).get("skill_calls") or 0) > 0),
            "hook_hint_rate": _rate(valid, lambda r: (ctx(r).get("hint_router", 0) + ctx(r).get("hint_skill", 0)) > 0),
            "rules_in_context": _rate(valid, lambda r: bool(ctx(r).get("rules_in_context"))),
            "rules_read": _rate(valid, lambda r: (r.get("depth") or {}).get("rules_read", 0) > 0),
            "rules_named": _rate(valid, lambda r: (r.get("depth") or {}).get("rules_named", 0) > 0),
            "further_skill": _rate(valid, lambda r: bool((r.get("depth") or {}).get("further_skill"))),
            "past_router": _rate(valid, lambda r: bool((r.get("depth") or {}).get("past_router"))),
            "mean_rules_lines_seen": round(sum(ctx(r).get("rules_lines_seen", 0) for r in valid) / len(valid), 1) if valid else None,
            "hidden_pass": round(sum(hp) / len(hp), 3) if hp else None,
            "mean_cost_usd": round(sum(costs) / len(costs), 4) if costs else None,
            "mean_turns": round(sum(turns) / len(turns), 2) if turns else None,
        }
    c, t = out["arms"]["control"], out["arms"]["treatment"]
    for label, a in (("control", c), ("treatment", t)):
        if not a["rules_in_context"]["n"]:
            out["invalid"].append("%s has no valid rows" % label)
    if (c["hook_hint_rate"]["k"] or 0) > 0:
        out["invalid"].append("the control arm received the hook's text: the arms are not separated")
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    if any((a["skill_call_rate"]["rate"] or 0) < MANIPULATION_MIN for a in (c, t)) \
            or (t["hook_hint_rate"]["rate"] or 0) < MANIPULATION_MIN:
        out["verdict"] = "MANIPULATION FAILED"
        return out
    diff = t["rules_in_context"]["rate"] - c["rules_in_context"]["rate"]
    p = fisher_one_sided(c["rules_in_context"]["k"], c["rules_in_context"]["n"],
                         t["rules_in_context"]["k"], t["rules_in_context"]["n"])
    out["primary"] = {"diff": round(diff, 3), "fisher_one_sided_p": round(p, 4)}
    out["verdict"] = ("SUPPORTED" if p < V5_ALPHA and diff >= V5_MIN_DIFF
                      else "NULL" if diff <= V5_NULL_MAX else "INCONCLUSIVE")
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in (c, t))
    return out


def rules_summary(rows: list) -> dict:
    """cases-v4, per arm: spec pass rate, rule tests passed / total (pooled), mean per-run rule share,
    and per case. Rows whose rule split was withheld or whose scoring failed are counted, not used."""
    out = {}
    for arm in sorted({r["arm"] for r in rows}):
        mine = [r for r in rows if r["arm"] == arm]
        scored = [r for r in mine if not excluded(r) and (r.get("hidden") or {}).get("rules")]
        unscored = len(mine) - len(scored)
        k = sum(r["hidden"]["rules"]["passed"] for r in scored)
        n = sum(r["hidden"]["rules"]["total"] for r in scored)
        shares = [r["hidden"]["rules"]["passed"] / r["hidden"]["rules"]["total"] for r in scored]
        out[arm] = {
            "rows": len(mine), "unscored_or_excluded": unscored,
            "spec_ok": _rate(scored, lambda r: r["hidden"].get("spec_ok") is True),
            "rule_tests_passed": {"k": k, "n": n, "rate": round(k / n, 3) if n else None},
            "mean_run_rule_share": round(sum(shares) / len(shares), 3) if shares else None,
            "runs_all_rules_passed": _rate(scored, lambda r: r["hidden"]["rules"]["passed"] == r["hidden"]["rules"]["total"]),
            "per_case": {r["case"]: "%d/%d%s" % (r["hidden"]["rules"]["passed"], r["hidden"]["rules"]["total"],
                                                  "" if r["hidden"].get("spec_ok") else " spec-FAIL")
                         for r in sorted(scored, key=lambda r: r["case"])},
        }
    return out


def main(argv=None):
    args = argv or sys.argv[1:]
    if "--rules" in args:   # analyze --rules <runs.jsonl>   (cases-v4, descriptive)
        path = [a for a in args if a != "--rules"][0]
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        print(json.dumps(rules_summary(rows), indent=2, default=str))
        return
    if "--v6" in args:      # analyze --v6 <runs.jsonl>
        path = [a for a in args if a != "--v6"][0]
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v6(rows), indent=2, default=str))
        return
    if "--v5" in args:      # analyze --v5 <control runs.jsonl> <treatment runs.jsonl>
        c_path, t_path = [a for a in args if a != "--v5"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v5(load(c_path), load(t_path)), indent=2, default=str))
        return
    hyps = HYPOTHESES_V4 if "--v4" in args else HYPOTHESES_V2 if "--v2" in args else HYPOTHESES
    path = [a for a in args if a not in ("--v2", "--v4")][0]
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    print(json.dumps(analyze(rows, hyps, manipulation_check="--v4" in args), indent=2, default=str))


if __name__ == "__main__":
    main()
