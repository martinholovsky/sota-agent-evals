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


V7_ARMS = ("bare", "installed", "installed+depth", "installed+named")
V7_MIN_DIFF, V7_NULL_MAX, V7_ALPHA = 0.09, 0.02, 0.05
# (name, control, treatment, manipulation: (metric on the treatment arm, minimum share)).
# The first is the PRIMARY; the others were added before any measurement run (PRE-REGISTRATION-v7
# amendment 1) so that one invocation answers every open variant, and carry no verdict of their own
# beyond the same rule applied separately.
V7_COMPARISONS = [
    ("primary: rules named", "installed", "installed+named", ("rules_in_context", 0.8)),
    ("secondary: depth hook", "installed", "installed+depth", ("hook_hint_rate", MANIPULATION_MIN)),
    ("secondary: library installed", "bare", "installed", ("skill_call_rate", MANIPULATION_MIN)),
]


def sign_flip_one_sided(diffs: list) -> float:
    """Exact paired permutation test: P(sum of randomly signed |d| >= observed sum). Cases with
    d == 0 contribute nothing under any sign, so only the non-zero ones are enumerated."""
    nz = [abs(d) for d in diffs if d]
    obs = sum(diffs)
    if not nz:
        return 1.0
    hits = 0
    for mask in range(1 << len(nz)):
        tot = sum(v if (mask >> i) & 1 else -v for i, v in enumerate(nz))
        hits += tot >= obs - 1e-9
    return hits / (1 << len(nz))


def _rules(r: dict):
    return (r.get("hidden") or {}).get("rules")


def _arm_stats(mine: list) -> tuple:
    excl = defaultdict(int)
    for r in mine:
        why = excluded(r) or ("rule results unscored" if not _rules(r) else None)
        if why:
            excl[why] += 1
    valid = [r for r in mine if not excluded(r) and _rules(r)]
    k = sum(_rules(r)["passed"] for r in valid)
    n = sum(_rules(r)["total"] for r in valid)
    costs = [(r.get("result") or {}).get("total_cost_usd") or 0.0 for r in valid]
    turns = [(r.get("result") or {}).get("num_turns") or 0 for r in valid]
    return valid, {
        "rows": len(mine), "excluded": dict(excl),
        "excluded_share": round(sum(excl.values()) / len(mine), 3) if mine else None,
        "rule_tests_passed": {"k": k, "n": n, "rate": round(k / n, 3) if n else None},
        "runs_all_rules_passed": _rate(valid, lambda r: _rules(r)["passed"] == _rules(r)["total"]),
        "spec_ok": _rate(valid, lambda r: r["hidden"].get("spec_ok") is True),
        "rules_in_context": _rate(valid, lambda r: bool(ctx(r).get("rules_in_context"))),
        "hook_hint_rate": _rate(valid, lambda r: (ctx(r).get("hint_router", 0) + ctx(r).get("hint_skill", 0)) > 0),
        "skill_call_rate": _rate(valid, lambda r: ((r.get("contamination") or {}).get("skill_calls") or 0) > 0),
        "mean_rules_lines_seen": round(sum(ctx(r).get("rules_lines_seen", 0) for r in valid) / len(valid), 1) if valid else None,
        "mean_cost_usd": round(sum(costs) / len(costs), 4) if costs else None,
        "mean_turns": round(sum(turns) / len(turns), 2) if turns else None,
    }


def _paired(c_valid: list, t_valid: list) -> dict:
    """Pooled rule tests over the cases scored in BOTH arms (a case's sample mean), and the exact
    one-sided sign-flip test over the per-case differences."""
    by = []
    for valid in (c_valid, t_valid):
        d = defaultdict(list)
        for r in valid:
            d[r["case"]].append(r)
        by.append(d)
    paired = sorted(set(by[0]) & set(by[1]))
    mean = lambda rs, key: sum(_rules(r)[key] for r in rs) / len(rs)
    diffs, tk, ck, pn, per_case = [], 0.0, 0.0, 0.0, {}
    for case in paired:
        cp, tp, tot = mean(by[0][case], "passed"), mean(by[1][case], "passed"), mean(by[1][case], "total")
        diffs.append(tp - cp)
        tk += tp; ck += cp; pn += tot
        per_case[case] = "%g -> %g of %g" % (cp, tp, tot)
    diff = (tk - ck) / pn if pn else 0.0
    p = sign_flip_one_sided(diffs)
    return {"paired_cases": len(paired), "control_rate": round(ck / pn, 3) if pn else None,
            "treatment_rate": round(tk / pn, 3) if pn else None, "diff": round(diff, 3),
            "sign_flip_one_sided_p": round(p, 4), "cases_up": sum(d > 0 for d in diffs),
            "cases_down": sum(d < 0 for d in diffs), "per_case": per_case,
            "verdict": ("SUPPORTED" if p < V7_ALPHA and diff >= V7_MIN_DIFF
                        else "NULL" if diff <= V7_NULL_MAX else "INCONCLUSIVE")}


def analyze_v7(rows: list) -> dict:
    """v7 (PRE-REGISTRATION-v7.md): does READING the cited rules change the outcome on cases-v4?
    Primary = `installed` vs `installed+named`, pooled RULE tests paired by case, exact one-sided
    sign-flip test. Secondaries (amendment 1) apply the same rule to the depth hook and to the
    library itself. Validity covers the whole file; manipulation is checked per comparison."""
    out = {"arms": {}, "invalid": [], "secondary": {}}
    shas = {r.get("router_sha") for r in rows}
    if len(shas) != 1 or None in shas:
        out["invalid"].append("file mixes routers or lacks router_sha: %s" % sorted(map(str, shas)))
    present = {r["arm"] for r in rows}
    stray = sorted(present - set(V7_ARMS))
    if stray:
        out["invalid"].append("unexpected arms %s" % stray)
    if any(r.get("named_rules") for r in rows if r["arm"] != "installed+named"):
        out["invalid"].append("a row outside installed+named had rules files named: the arms are not separated")
    if any(not r.get("named_rules") for r in rows if r["arm"] == "installed+named"):
        out["invalid"].append("an installed+named row's prompt named no rules files")
    if any(ctx(r).get("hint_router", 0) + ctx(r).get("hint_skill", 0) for r in rows if r["arm"] != "installed+depth"):
        out["invalid"].append("a row outside installed+depth received the depth hook's text")
    valid = {}
    for arm in V7_ARMS:
        if arm not in present:
            continue
        valid[arm], out["arms"][arm] = _arm_stats([r for r in rows if r["arm"] == arm])
        if any(not ctx(r).get("transcripts") for r in valid[arm]):
            out["invalid"].append("%s has valid rows with no CLI transcript to score" % arm)
        if not out["arms"][arm]["rule_tests_passed"]["n"]:
            out["invalid"].append("%s has no valid rows" % arm)
    for arm in ("installed", "installed+named"):
        if arm not in present:
            out["invalid"].append("primary arm %s has no rows" % arm)
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    for i, (name, c, t, (metric, floor)) in enumerate(V7_COMPARISONS):
        if c not in valid or t not in valid:
            res = {"verdict": "NOT RUN"}
        elif (out["arms"][t][metric]["rate"] or 0) < floor:
            res = {"verdict": "MANIPULATION FAILED", "manipulation": {metric: out["arms"][t][metric]}}
        else:
            res = _paired(valid[c], valid[t])
        res["control"], res["treatment"] = c, t
        if i == 0:
            out["primary"], out["verdict"] = res, res["verdict"]
        else:
            out["secondary"][name] = res
    c, t = out["arms"]["installed"], out["arms"]["installed+named"]
    out["secondary_all_rules_fisher_p"] = round(fisher_one_sided(
        c["runs_all_rules_passed"]["k"], c["runs_all_rules_passed"]["n"],
        t["runs_all_rules_passed"]["k"], t["runs_all_rules_passed"]["n"]), 4)
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


def analyze_v8(rows: list, v7_rows: list) -> dict:
    """v8 (PRE-REGISTRATION-v8.md): ROADMAP 73 (d'), the depth hook asking for a FULL read of one or
    two chosen rules files. Treatment = this file's `installed+depth` rows; control = v7's
    `installed` rows (same root skills/, router, model and cases), reused to save a paid arm. The
    same paired rule as v7. Validity: one router across both files, only the treatment arm here, the
    hook's text reached no control row; manipulation: the hook's text reached >= 0.5 of the runs."""
    out = {"arms": {}, "invalid": []}
    control = [r for r in v7_rows if r["arm"] == "installed"]
    shas = {r.get("router_sha") for r in rows + control}
    if len(shas) != 1 or None in shas:
        out["invalid"].append("files mix routers or lack router_sha: %s" % sorted(map(str, shas)))
    stray = sorted({r["arm"] for r in rows} - {"installed+depth"})
    if stray:
        out["invalid"].append("unexpected arms %s" % stray)
    if any(r.get("named_rules") for r in rows + control):
        out["invalid"].append("a row's prompt named rules files")
    if any(ctx(r).get("hint_router", 0) + ctx(r).get("hint_skill", 0) for r in control):
        out["invalid"].append("a control row received the depth hook's text")
    valid = {}
    for label, mine in (("control (v7 installed)", control), ("treatment (installed+depth, full read)", rows)):
        valid[label], out["arms"][label] = _arm_stats(mine)
        if any(not ctx(r).get("transcripts") for r in valid[label]):
            out["invalid"].append("%s has valid rows with no CLI transcript to score" % label)
        if not out["arms"][label]["rule_tests_passed"]["n"]:
            out["invalid"].append("%s has no valid rows" % label)
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    c, t = list(valid)
    if (out["arms"][t]["hook_hint_rate"]["rate"] or 0) < MANIPULATION_MIN:
        out["verdict"] = "MANIPULATION FAILED"
        return out
    out["primary"] = _paired(valid[c], valid[t])
    out["verdict"] = out["primary"]["verdict"]
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


V9_ARMS = ("installed+code", "installed+linked")


def analyze_v9(rows: list, v7_rows: list, v8_rows: list) -> dict:
    """v9 (PRE-REGISTRATION-v9.md): ROADMAP 73 (h) and the linking question, one invocation.
    Primary: v7's `installed` rows -> `installed+code` (the rules file chosen from the code written).
    Secondary: v7's `installed` rows -> `installed+linked` (the same table as links in sota-python's
    SKILL.md, with v8's full-read hook). Descriptive: v8's rows -> `installed+linked`, which differ
    only in the table. Each comparison: the v7 paired rule; manipulation: its marker reached >= 0.5
    of the treatment's runs (the hook's text, or the table in a tool result)."""
    out = {"arms": {}, "invalid": [], "secondary": {}, "descriptive": {}}
    control = [r for r in v7_rows if r["arm"] == "installed"]
    v8 = [r for r in v8_rows if r["arm"] == "installed+depth"]
    shas = {r.get("router_sha") for r in rows + control + v8}
    if len(shas) != 1 or None in shas:
        out["invalid"].append("files mix routers or lack router_sha: %s" % sorted(map(str, shas)))
    stray = sorted({r["arm"] for r in rows} - set(V9_ARMS))
    if stray:
        out["invalid"].append("unexpected arms %s" % stray)
    if any(r.get("named_rules") for r in rows + control + v8):
        out["invalid"].append("a row's prompt named rules files")
    leaks = {"installed+code": ("hint_router", "hint_skill", "linked_table"),
             "installed+linked": ("hint_code",)}
    for r in rows:
        if any(ctx(r).get(k, 0) for k in leaks.get(r["arm"], ())):
            out["invalid"].append("a %s row received another arm's treatment" % r["arm"])
            break
    if any(ctx(r).get(k, 0) for r in control for k in ("hint_router", "hint_skill", "hint_code", "linked_table")):
        out["invalid"].append("a control row received a treatment")
    groups = {"control (v7 installed)": control, "v8 (full-read hook)": v8,
              "installed+code": [r for r in rows if r["arm"] == "installed+code"],
              "installed+linked": [r for r in rows if r["arm"] == "installed+linked"]}
    valid = {}
    for label, mine in groups.items():
        valid[label], out["arms"][label] = _arm_stats(mine)
        out["arms"][label]["code_hint_rate"] = _rate(valid[label], lambda r: ctx(r).get("hint_code", 0) > 0)
        out["arms"][label]["linked_table_rate"] = _rate(valid[label], lambda r: ctx(r).get("linked_table", 0) > 0)
        if any(not ctx(r).get("transcripts") for r in valid[label]):
            out["invalid"].append("%s has valid rows with no CLI transcript to score" % label)
        if not out["arms"][label]["rule_tests_passed"]["n"]:
            out["invalid"].append("%s has no valid rows" % label)
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    c = "control (v7 installed)"
    plan = (("primary", c, "installed+code", "code_hint_rate"),
            ("secondary: linked index", c, "installed+linked", "linked_table_rate"),
            ("descriptive: v8 -> linked (the table alone)", "v8 (full-read hook)", "installed+linked", "linked_table_rate"))
    for name, lo, hi, manip in plan:
        res = {"control": lo, "treatment": hi, "manipulation": manip,
               "manipulation_rate": out["arms"][hi][manip]["rate"]}
        if (res["manipulation_rate"] or 0) < MANIPULATION_MIN:
            res["verdict"] = "MANIPULATION FAILED"
        else:
            res.update(_paired(valid[lo], valid[hi]))
        if name == "primary":
            out["primary"] = res
            out["verdict"] = res["verdict"]
        elif name.startswith("secondary"):
            out["secondary"][name] = res
        else:
            res.pop("verdict", None)      # descriptive: no verdict attached
            out["descriptive"][name] = res
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


def analyze_v10(rows: list, v9_rows: list, v7_rows: list) -> dict:
    """v10 (PRE-REGISTRATION-v10.md): ROADMAP 73 (j), one arm. The code-rules hook's text adds that the
    named rules are part of the task. Primary: v9's `installed+code` rows -> `installed+apply`, which
    differ only in that wording. Secondary: v7's `installed` rows -> `installed+apply` (the arm against
    the plain install). Each comparison: the v7 paired rule; manipulation: the new wording reached
    >= 0.5 of the treatment's runs."""
    out = {"arms": {}, "invalid": [], "secondary": {}}
    code = [r for r in v9_rows if r["arm"] == "installed+code"]
    control = [r for r in v7_rows if r["arm"] == "installed"]
    shas = {r.get("router_sha") for r in rows + code + control}
    if len(shas) != 1 or None in shas:
        out["invalid"].append("files mix routers or lack router_sha: %s" % sorted(map(str, shas)))
    stray = sorted({r["arm"] for r in rows} - {"installed+apply"})
    if stray:
        out["invalid"].append("unexpected arms %s" % stray)
    if any(r.get("named_rules") for r in rows + code + control):
        out["invalid"].append("a row's prompt named rules files")
    if any(ctx(r).get(k, 0) for r in rows for k in ("hint_router", "hint_skill", "linked_table")):
        out["invalid"].append("an installed+apply row received another arm's treatment")
    if any(ctx(r).get("hint_apply", 0) for r in code):
        out["invalid"].append("a v9 installed+code row carries the v10 wording: wrong file")
    if any(ctx(r).get(k, 0) for r in control for k in ("hint_router", "hint_skill", "hint_code", "linked_table", "hint_apply")):
        out["invalid"].append("a control row received a treatment")
    groups = {"control (v7 installed)": control, "v9 code hook": code, "installed+apply": rows}
    valid = {}
    for label, mine in groups.items():
        valid[label], out["arms"][label] = _arm_stats(mine)
        out["arms"][label]["code_hint_rate"] = _rate(valid[label], lambda r: ctx(r).get("hint_code", 0) > 0)
        out["arms"][label]["apply_hint_rate"] = _rate(valid[label], lambda r: ctx(r).get("hint_apply", 0) > 0)
        if any(not ctx(r).get("transcripts") for r in valid[label]):
            out["invalid"].append("%s has valid rows with no CLI transcript to score" % label)
        if not out["arms"][label]["rule_tests_passed"]["n"]:
            out["invalid"].append("%s has no valid rows" % label)
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    for name, lo in (("primary", "v9 code hook"), ("secondary: vs the plain install", "control (v7 installed)")):
        res = {"control": lo, "treatment": "installed+apply", "manipulation": "apply_hint_rate",
               "manipulation_rate": out["arms"]["installed+apply"]["apply_hint_rate"]["rate"]}
        if (res["manipulation_rate"] or 0) < MANIPULATION_MIN:
            res["verdict"] = "MANIPULATION FAILED"
        else:
            res.update(_paired(valid[lo], valid["installed+apply"]))
        if name == "primary":
            out["primary"] = res
            out["verdict"] = res["verdict"]
        else:
            out["secondary"][name] = res
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


def analyze_v11(rows: list, v10_rows: list, v9_rows: list) -> dict:
    """v11 (PRE-REGISTRATION-v11.md): the code-rules hook with a bare MANDATORY label. Primary: v9's
    `installed+code` rows -> `installed+label` (does the label alone help?). Secondary: `installed+label`
    -> v10's `installed+apply` (does v10's wording beat the label?). Both: the v7 paired rule;
    manipulation: the label reached >= 0.5 of the label arm's runs (and v10's wording, of v10's)."""
    out = {"arms": {}, "invalid": [], "secondary": {}}
    code = [r for r in v9_rows if r["arm"] == "installed+code"]
    apply = [r for r in v10_rows if r["arm"] == "installed+apply"]
    shas = {r.get("router_sha") for r in rows + code + apply}
    if len(shas) != 1 or None in shas:
        out["invalid"].append("files mix routers or lack router_sha: %s" % sorted(map(str, shas)))
    stray = sorted({r["arm"] for r in rows} - {"installed+label"})
    if stray:
        out["invalid"].append("unexpected arms %s" % stray)
    if any(r.get("named_rules") for r in rows + code + apply):
        out["invalid"].append("a row's prompt named rules files")
    if any(ctx(r).get(k, 0) for r in rows for k in ("hint_router", "hint_skill", "linked_table", "hint_apply")):
        out["invalid"].append("an installed+label row received another arm's treatment")
    if any(ctx(r).get("hint_label", 0) for r in code + apply):
        out["invalid"].append("a v9 or v10 row carries the v11 label: wrong file")
    groups = {"v9 code hook": code, "installed+label": rows, "v10 apply": apply}
    valid = {}
    for label, mine in groups.items():
        valid[label], out["arms"][label] = _arm_stats(mine)
        out["arms"][label]["label_hint_rate"] = _rate(valid[label], lambda r: ctx(r).get("hint_label", 0) > 0)
        out["arms"][label]["apply_hint_rate"] = _rate(valid[label], lambda r: ctx(r).get("hint_apply", 0) > 0)
        if any(not ctx(r).get("transcripts") for r in valid[label]):
            out["invalid"].append("%s has valid rows with no CLI transcript to score" % label)
        if not out["arms"][label]["rule_tests_passed"]["n"]:
            out["invalid"].append("%s has no valid rows" % label)
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    plan = (("primary", "v9 code hook", "installed+label", "label_hint_rate", "installed+label"),
            ("secondary: label -> v10 wording", "installed+label", "v10 apply", "apply_hint_rate", "v10 apply"))
    for name, lo, hi, manip, marked in plan:
        res = {"control": lo, "treatment": hi, "manipulation": manip,
               "manipulation_rate": out["arms"][marked][manip]["rate"]}
        if (res["manipulation_rate"] or 0) < MANIPULATION_MIN:
            res["verdict"] = "MANIPULATION FAILED"
        else:
            res.update(_paired(valid[lo], valid[hi]))
        if name == "primary":
            out["primary"] = res
            out["verdict"] = res["verdict"]
        else:
            out["secondary"][name] = res
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


V12_REACH_MIN_DIFF = 0.20   # 4 of 20 runs
V12_REACH_NULL_MAX = 0.05   # 1 of 20 runs


def annotate_reach(rows: list, results_dir, cases_path) -> list:
    """Re-score reused rows (v7's) with v12's reach fields, from their kept transcripts. A row
    whose transcript directory is missing is returned WITHOUT the fields, so analyze_v12 refuses it
    rather than scoring it 'not reached'."""
    from pathlib import Path
    from .score import cited_reach, HOOK_MARKERS
    cases = {}
    for l in open(cases_path, encoding="utf-8"):
        if l.strip():
            c = json.loads(l)
            if "id" in c:
                cases[c["id"]] = c.get("rules_files") or []
    out = []
    for r in rows:
        tdir = Path(results_dir) / "transcripts" / ("%s__%s__%d" % (r["case"], r["arm"].replace("+", "_"), r["sample"]))
        r = dict(r)
        if tdir.is_dir() and any(tdir.rglob("*.jsonl")):
            raw = "".join(f.read_text(encoding="utf-8", errors="replace") for f in tdir.rglob("*.jsonl"))
            r["context"] = dict(r.get("context") or {}, **cited_reach(tdir, cases[r["case"]]),
                                links_router=raw.count(HOOK_MARKERS["links_router"]),
                                table_router=raw.count(HOOK_MARKERS["table_router"]))
        out.append(r)
    return out


def _binom_tail(k: int, n: int) -> float:
    """P(X >= k), X ~ Binomial(n, 1/2): the exact one-sided sign test over discordant pairs."""
    from math import comb
    return sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def _paired_reach(c_valid: list, t_valid: list) -> dict:
    c = {r["case"]: bool(ctx(r).get("cited_reached")) for r in c_valid}
    t = {r["case"]: bool(ctx(r).get("cited_reached")) for r in t_valid}
    paired = sorted(set(c) & set(t))
    up = [k for k in paired if t[k] and not c[k]]
    down = [k for k in paired if c[k] and not t[k]]
    n = len(paired)
    diff = (sum(t[k] for k in paired) - sum(c[k] for k in paired)) / n if n else 0.0
    p = _binom_tail(len(up), len(up) + len(down))
    return {"paired_cases": n, "control_rate": round(sum(c[k] for k in paired) / n, 3) if n else None,
            "treatment_rate": round(sum(t[k] for k in paired) / n, 3) if n else None,
            "diff": round(diff, 3), "sign_test_one_sided_p": round(p, 4), "cases_up": up, "cases_down": down,
            "verdict": ("SUPPORTED" if p < V7_ALPHA and diff >= V12_REACH_MIN_DIFF
                        else "NULL" if diff <= V12_REACH_NULL_MAX else "INCONCLUSIVE")}


def analyze_v12(rows: list, v7_rows: list) -> dict:
    """v12 (PRE-REGISTRATION-v12.md): links vs names. Primary: v7's `installed` rows (annotated by
    annotate_reach) -> `installed+links`, on whether the run reached a cited rules file (paired by
    case, exact sign test over discordant pairs). Secondary: rule tests, v7's paired rule.
    Manipulation: the router's links reached >= 0.5 of the treatment's runs and none of the control's."""
    out = {"arms": {}, "invalid": [], "secondary": {}}
    control = [r for r in v7_rows if r["arm"] == "installed"]
    stray = sorted({r["arm"] for r in rows} - {"installed+links"})
    if stray:
        out["invalid"].append("unexpected arms %s" % stray)
    t_sha = {r.get("router_sha") for r in rows}
    c_sha = {r.get("router_sha") for r in control}
    if len(t_sha) != 1 or len(c_sha) != 1 or None in t_sha | c_sha or t_sha == c_sha:
        out["invalid"].append("each arm needs one router, and they must differ: %s vs %s"
                              % (sorted(map(str, c_sha)), sorted(map(str, t_sha))))
    if any(r.get("named_rules") for r in rows + control):
        out["invalid"].append("a row's prompt named rules files")
    hints = ("hint_router", "hint_skill", "hint_code", "linked_table", "hint_apply", "hint_label")
    if any(ctx(r).get(k, 0) for r in rows + control for k in hints):
        out["invalid"].append("a row received a hook or table treatment")
    if any("cited_reached" not in ctx(r) or "links_router" not in ctx(r) for r in rows + control):
        out["invalid"].append("a row lacks the v12 reach fields (control not annotated, or no transcript)")
    if any(ctx(r).get("links_router", 0) for r in control):
        out["invalid"].append("a control row saw the links router: wrong file")
    valid = {}
    for label, mine in (("v7 installed", control), ("installed+links", rows)):
        valid[label], out["arms"][label] = _arm_stats(mine)
        v = valid[label]
        out["arms"][label].update({
            "links_rate": _rate(v, lambda r: ctx(r).get("links_router", 0) > 0),
            "cited_reached": _rate(v, lambda r: bool(ctx(r).get("cited_reached"))),
            "past_router": _rate(v, lambda r: bool((r.get("depth") or {}).get("past_router"))),
            "rules_read_errors": sum(ctx(r).get("rules_read_errors", 0) for r in v)})
        if not out["arms"][label]["rule_tests_passed"]["n"]:
            out["invalid"].append("%s has no valid rows" % label)
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    rate = out["arms"]["installed+links"]["links_rate"]["rate"] or 0
    if rate < MANIPULATION_MIN:
        out["primary"] = {"verdict": "MANIPULATION FAILED", "links_rate": rate}
        out["verdict"] = "MANIPULATION FAILED"
        return out
    out["primary"] = dict(_paired_reach(valid["v7 installed"], valid["installed+links"]), outcome="cited_reached")
    out["verdict"] = out["primary"]["verdict"]
    out["secondary"]["rule tests"] = _paired(valid["v7 installed"], valid["installed+links"])
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


def analyze_v13(rows: list, v12_rows: list) -> dict:
    """v13 (PRE-REGISTRATION-v13.md): SOTA-skills ROADMAP 73 (o), the router's trigger table. Primary:
    v12's `installed+links` rows (re-annotated by annotate_reach) -> `installed+table`, on whether the
    run reached a cited rules file, with v12's thresholds. Secondary: rule tests, v7's paired rule.
    Manipulation: the table reached >= 0.5 of the treatment's runs and none of the control's. The
    table carries v10's paragraph, so `hint_apply` is EXPECTED in the treatment and is not a hook;
    every other hook or table marker invalidates a row."""
    out = {"arms": {}, "invalid": [], "secondary": {}}
    control = [r for r in v12_rows if r["arm"] == "installed+links"]
    stray = sorted({r["arm"] for r in rows} - {"installed+table"})
    if stray:
        out["invalid"].append("unexpected arms %s" % stray)
    t_sha = {r.get("router_sha") for r in rows}
    c_sha = {r.get("router_sha") for r in control}
    if len(t_sha) != 1 or len(c_sha) != 1 or None in t_sha | c_sha or t_sha == c_sha:
        out["invalid"].append("each arm needs one router, and they must differ: %s vs %s"
                              % (sorted(map(str, c_sha)), sorted(map(str, t_sha))))
    if any(r.get("named_rules") for r in rows + control):
        out["invalid"].append("a row's prompt named rules files")
    hints = ("hint_router", "hint_skill", "hint_code", "linked_table", "hint_label")
    if any(ctx(r).get(k, 0) for r in rows + control for k in hints):
        out["invalid"].append("a row received a hook or index-table treatment")
    if any(ctx(r).get("hint_apply", 0) for r in control):
        out["invalid"].append("a control row saw the part-of-the-task paragraph")
    if any("cited_reached" not in ctx(r) or "table_router" not in ctx(r) for r in rows + control):
        out["invalid"].append("a row lacks the v13 fields (control not re-annotated, or no transcript)")
    if any(ctx(r).get("table_router", 0) for r in control):
        out["invalid"].append("a control row saw the table router: wrong file")
    valid = {}
    for label, mine in (("v12 installed+links", control), ("installed+table", rows)):
        valid[label], out["arms"][label] = _arm_stats(mine)
        v = valid[label]
        out["arms"][label].update({
            "table_rate": _rate(v, lambda r: ctx(r).get("table_router", 0) > 0),
            "cited_reached": _rate(v, lambda r: bool(ctx(r).get("cited_reached"))),
            "past_router": _rate(v, lambda r: bool((r.get("depth") or {}).get("past_router"))),
            "rules_read_errors": sum(ctx(r).get("rules_read_errors", 0) for r in v)})
        if not out["arms"][label]["rule_tests_passed"]["n"]:
            out["invalid"].append("%s has no valid rows" % label)
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    rate = out["arms"]["installed+table"]["table_rate"]["rate"] or 0
    if rate < MANIPULATION_MIN:
        out["primary"] = {"verdict": "MANIPULATION FAILED", "table_rate": rate}
        out["verdict"] = "MANIPULATION FAILED"
        return out
    out["primary"] = dict(_paired_reach(valid["v12 installed+links"], valid["installed+table"]),
                          outcome="cited_reached")
    out["verdict"] = out["primary"]["verdict"]
    out["secondary"]["rule tests"] = _paired(valid["v12 installed+links"], valid["installed+table"])
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


V14_WEAK = ("w01", "w15", "w18")   # cases-v5 SELECTION.md: weak citations, a sensitivity cut


def cases_v5_uncited(tasks_dir) -> tuple:
    """Cases whose rule tests are ALL uncited. Primary = cited rule tests, scored per case, so a case
    mixing cited and uncited tests would need per-test results: refused rather than approximated."""
    from pathlib import Path
    out = []
    for f in sorted(Path(tasks_dir).glob("w*/rules.json")):
        cited = ["quote" in e for e in json.loads(f.read_text(encoding="utf-8"))]
        if not cited or (any(cited) and not all(cited)):
            raise SystemExit("%s mixes cited and uncited rule tests (or has none)" % f)
        if not any(cited):
            out.append(f.parent.name)
    if not out and not list(Path(tasks_dir).glob("w*/rules.json")):
        raise SystemExit("no rules.json under %s" % tasks_dir)
    return tuple(out)


def analyze_v14(rows: list, control: list, uncited: tuple) -> dict:
    """v14 (PRE-REGISTRATION-v14.md): the SHIPPED DEFAULT out of sample. cases-v5's calibration rows
    (`installed+links`, the library without the router table and without the code-rules hook) ->
    `installed+table+code` (the table root plus the hook). Primary: CITED rule tests (cases-v5
    SELECTION.md), v7's paired rule. Secondary: all rule tests; reach (v12's thresholds). Sensitivity:
    cited without the weak citations. Manipulation: the hook spoke in >= 0.5 of the treatment's runs.
    The table and the hook both carry v10's paragraph, so `hint_apply` is EXPECTED in the treatment."""
    out = {"arms": {}, "invalid": [], "secondary": {}}
    stray = sorted({r["arm"] for r in rows} - {"installed+table+code"}) + \
        sorted({r["arm"] for r in control} - {"installed+links"})
    if stray:
        out["invalid"].append("unexpected arms %s" % stray)
    t_sha = {r.get("router_sha") for r in rows}
    c_sha = {r.get("router_sha") for r in control}
    if len(t_sha) != 1 or len(c_sha) != 1 or None in t_sha | c_sha or t_sha == c_sha:
        out["invalid"].append("each arm needs one router, and they must differ: %s vs %s"
                              % (sorted(map(str, c_sha)), sorted(map(str, t_sha))))
    if any(r.get("named_rules") for r in rows + control):
        out["invalid"].append("a row's prompt named rules files")
    if any(ctx(r).get(k, 0) for r in rows + control for k in ("hint_router", "hint_skill", "linked_table", "hint_label")):
        out["invalid"].append("a row received a depth-hook, index-table or label treatment")
    if any(ctx(r).get(k, 0) for r in control for k in ("hint_code", "hint_apply", "table_router")):
        out["invalid"].append("a control row received the treatment")
    if any("cited_reached" not in ctx(r) or "table_router" not in ctx(r) for r in rows + control):
        out["invalid"].append("a row lacks the reach fields (no transcript)")
    valid = {}
    for label, mine in (("control (installed+links)", control), ("installed+table+code", rows)):
        valid[label], out["arms"][label] = _arm_stats(mine)
        v = valid[label]
        out["arms"][label].update({
            "code_hint_rate": _rate(v, lambda r: ctx(r).get("hint_code", 0) > 0),
            "table_rate": _rate(v, lambda r: ctx(r).get("table_router", 0) > 0),
            "cited_reached": _rate(v, lambda r: bool(ctx(r).get("cited_reached"))),
            "rules_read_errors": sum(ctx(r).get("rules_read_errors", 0) for r in v)})
        if not out["arms"][label]["rule_tests_passed"]["n"]:
            out["invalid"].append("%s has no valid rows" % label)
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    rate = out["arms"]["installed+table+code"]["code_hint_rate"]["rate"] or 0
    if rate < MANIPULATION_MIN:
        out["primary"] = {"verdict": "MANIPULATION FAILED", "code_hint_rate": rate}
        out["verdict"] = "MANIPULATION FAILED"
        return out
    c, t = valid["control (installed+links)"], valid["installed+table+code"]
    keep = lambda vs, drop: [r for r in vs if r["case"] not in drop]
    out["primary"] = dict(_paired(keep(c, uncited), keep(t, uncited)), outcome="cited rule tests",
                          excluded_uncited_cases=list(uncited))
    out["verdict"] = out["primary"]["verdict"]
    out["secondary"]["all rule tests"] = _paired(c, t)
    out["secondary"]["reach"] = _paired_reach(c, t)
    out["secondary"]["sensitivity: cited without weak citations"] = _paired(
        keep(c, uncited + V14_WEAK), keep(t, uncited + V14_WEAK))
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


V15_ROUTERS = {"control": "60edc3eae536ec8c", "treatment": "75b678d9bdad7b29"}   # v14's two roots
V15_ARMS = {"cp": "installed+links+pressure", "tp": "installed+table+code+pressure",
            "cn": "installed+links", "tn": "installed+table+code"}


def analyze_v15(cp: list, tp: list, cn: list, tn: list, uncited: tuple) -> dict:
    """v15 (PRE-REGISTRATION-v15.md): v14 under competing pressure. Primary: the shipped default vs
    the control, BOTH with runner.PRESSURE appended, on cited rule tests, v7's paired rule. The
    unpressured rows are v14's (declared reuse) and enter only the secondaries: how far pressure
    moved each arm, and the interaction (the default's pressured advantage minus its neutral one),
    which is descriptive. If pressure did not lower the control's cited score, the primary still
    reads by its rule but the file says the pressure did not bind."""
    out = {"arms": {}, "invalid": [], "secondary": {}}
    groups = {"cp": cp, "tp": tp, "cn": cn, "tn": tn}
    for k, rows in groups.items():
        stray = sorted({r["arm"] for r in rows} - {V15_ARMS[k]})
        if stray:
            out["invalid"].append("%s file holds unexpected arms %s" % (k, stray))
        want = V15_ROUTERS["control" if k[0] == "c" else "treatment"]
        shas = {r.get("router_sha") for r in rows}
        if shas != {want}:
            out["invalid"].append("%s rows ran on router %s, not %s" % (k, sorted(map(str, shas)), want))
    if any(r.get("named_rules") for rows in groups.values() for r in rows):
        out["invalid"].append("a row's prompt named rules files")
    if any(ctx(r).get(k, 0) for rows in groups.values() for r in rows
           for k in ("hint_router", "hint_skill", "linked_table", "hint_label")):
        out["invalid"].append("a row received a depth-hook, index-table or label treatment")
    if any(ctx(r).get(k, 0) for r in cp + cn for k in ("hint_code", "hint_apply", "table_router")):
        out["invalid"].append("a control row received the treatment")
    if any(ctx(r).get("pressure", 0) for r in cn + tn):
        out["invalid"].append("an unpressured row carries the pressure sentence")
    if any("cited_reached" not in ctx(r) or "table_router" not in ctx(r) for rows in groups.values() for r in rows):
        out["invalid"].append("a row lacks the reach fields (no transcript)")
    valid = {}
    for k, rows in groups.items():
        valid[k], out["arms"][V15_ARMS[k]] = _arm_stats(rows)
        v = valid[k]
        out["arms"][V15_ARMS[k]].update({
            "pressure_rate": _rate(v, lambda r: ctx(r).get("pressure", 0) > 0),
            "code_hint_rate": _rate(v, lambda r: ctx(r).get("hint_code", 0) > 0),
            "cited_reached": _rate(v, lambda r: bool(ctx(r).get("cited_reached"))),
            "rules_read_errors": sum(ctx(r).get("rules_read_errors", 0) for r in v)})
        if not out["arms"][V15_ARMS[k]]["rule_tests_passed"]["n"]:
            out["invalid"].append("%s has no valid rows" % V15_ARMS[k])
    # the pressure is the prompt itself, so it must have reached EVERY pressured run
    if any(not ctx(r).get("pressure", 0) for r in valid.get("cp", []) + valid.get("tp", [])):
        out["invalid"].append("a pressured run's transcript lacks the pressure sentence")
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    rate = out["arms"][V15_ARMS["tp"]]["code_hint_rate"]["rate"] or 0
    if rate < MANIPULATION_MIN:
        out["primary"] = {"verdict": "MANIPULATION FAILED", "code_hint_rate": rate}
        out["verdict"] = "MANIPULATION FAILED"
        return out
    keep = lambda vs, drop=uncited: [r for r in vs if r["case"] not in drop]
    out["primary"] = dict(_paired(keep(valid["cp"]), keep(valid["tp"])), outcome="cited rule tests, both pressured",
                          excluded_uncited_cases=list(uncited))
    out["verdict"] = out["primary"]["verdict"]
    sec = out["secondary"]
    sec["all rule tests, pressured"] = _paired(valid["cp"], valid["tp"])
    sec["reach, pressured"] = _paired_reach(valid["cp"], valid["tp"])
    sec["sensitivity: cited without weak citations, pressured"] = _paired(
        keep(valid["cp"], uncited + V14_WEAK), keep(valid["tp"], uncited + V14_WEAK))
    # "treatment" = the UNPRESSURED rows, so "up" reads as "pressure lowered this arm"
    sec["pressure lowered the control (cited)"] = _paired(keep(valid["cp"]), keep(valid["cn"]))
    sec["pressure lowered the default (cited)"] = _paired(keep(valid["tp"]), keep(valid["tn"]))
    sec["pressure bound"] = sec["pressure lowered the control (cited)"]["diff"] > 0
    pressured, neutral = out["primary"], _paired(keep(valid["cn"]), keep(valid["tn"]))
    sec["interaction (descriptive, no verdict)"] = {
        "default minus control, pressured": pressured["diff"], "default minus control, neutral": neutral["diff"],
        "difference": round(pressured["diff"] - neutral["diff"], 3)}
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


# v16 (PRE-REGISTRATION-v16.md): ONE arm, two roots. Control = v14's rows (declared reuse), treatment
# = the same arm on SOTA-skills origin/main @ 3287dd07. The rows share an arm name, so the root is
# what separates them: the router hash (both files) and, for the treatment, the whole library's digest.
V16_ARM = "installed+table+code"
V16_ROUTERS = {"control": "75b678d9bdad7b29", "treatment": "ad7fb225bda66ec8"}
V16_ROOT_DIGEST = "452b21b4f34a5eb1"     # cli.root_digest() of `git archive 3287dd07` (and the guard's value)
# Primary thresholds, on the RELATIVE pooled difference in rules lines seen per run, fixed before any
# v16 run. 0.20 = about 186 lines a run over v14's 930.8, two-thirds of one more mid-size rules file
# read in full; 0.05 covers the measured size-only drift (+0.9%) and the +5.1% a prompt change moved
# depth at the same root (v14 -> v15's default arm).
V16_MIN_REL, V16_NULL_REL, V16_ALPHA = 0.20, 0.05, 0.05


def sign_flip_one_sided_exact(diffs: list) -> float:
    """sign_flip_one_sided() by meet-in-the-middle, so 20 non-zero cases (2^20 sign patterns) are
    exact and fast. Same tie rule (>= observed - 1e-9); the unit test checks both agree."""
    from bisect import bisect_left
    nz = [abs(d) for d in diffs if d]
    obs = sum(diffs)
    if not nz:
        return 1.0

    def sums(vals):
        out = [0.0]
        for v in vals:
            out = [s + v for s in out] + [s - v for s in out]
        return out
    half = len(nz) // 2
    left, right = sums(nz[:half]), sorted(sums(nz[half:]))
    hits = sum(len(right) - bisect_left(right, obs - 1e-9 - s) for s in left)
    return hits / (1 << len(nz))


def _lines(r: dict) -> float:
    return float(ctx(r).get("rules_lines_seen", 0))


def _paired_depth(c_valid: list, t_valid: list) -> dict:
    """Primary: rules lines seen per run (v6's content measure, `context.rules_lines_seen`), paired by
    case (a case's sample mean), exact one-sided sign-flip over the per-case differences."""
    by = []
    for valid in (c_valid, t_valid):
        d = defaultdict(list)
        for r in valid:
            d[r["case"]].append(_lines(r))
        by.append({k: sum(v) / len(v) for k, v in d.items()})
    paired = sorted(set(by[0]) & set(by[1]))
    diffs = [by[1][k] - by[0][k] for k in paired]
    ct, tt = sum(by[0][k] for k in paired), sum(by[1][k] for k in paired)
    rel = (tt - ct) / ct if ct else None
    p = sign_flip_one_sided_exact(diffs)
    verdict = ("INCONCLUSIVE" if rel is None
               else "SUPPORTED" if p < V16_ALPHA and rel >= V16_MIN_REL
               else "NULL" if rel <= V16_NULL_REL else "INCONCLUSIVE")
    n = len(paired)
    return {"outcome": "rules lines seen per run", "paired_cases": n,
            "control_mean": round(ct / n, 1) if n else None, "treatment_mean": round(tt / n, 1) if n else None,
            "mean_diff_lines": round((tt - ct) / n, 1) if n else None,
            "rel_diff": None if rel is None else round(rel, 4),
            "sign_flip_one_sided_p": round(p, 4), "cases_up": sum(d > 0 for d in diffs),
            "cases_down": sum(d < 0 for d in diffs), "cases_equal": sum(d == 0 for d in diffs),
            "per_case": {k: "%g -> %g" % (by[0][k], by[1][k]) for k in paired},
            "thresholds": {"alpha": V16_ALPHA, "supported_rel_min": V16_MIN_REL, "null_rel_max": V16_NULL_REL},
            "verdict": verdict}


def _no_verdict(res: dict) -> dict:
    """A secondary carries no verdict (PRE-REGISTRATION-v16): its rule's label is dropped."""
    return {k: v for k, v in res.items() if k != "verdict"}


def analyze_v16(rows: list, control: list, uncited: tuple) -> dict:
    """v16 (PRE-REGISTRATION-v16.md): does the shipped default on TODAY's library reach more rules-file
    text than it did on v14's root? Control: v14's `installed+table+code` rows (root 4a5fee40, declared
    reuse). Treatment: the same arm from origin/main @ 3287dd07. Primary: rules lines seen per run,
    paired by case, exact one-sided sign-flip; SUPPORTED iff p < 0.05 and the relative pooled difference
    >= 0.20, NULL iff it is <= 0.05, else INCONCLUSIVE. Secondaries carry no verdict."""
    out = {"arms": {}, "invalid": [], "secondary": {}}
    for label, mine in (("control", control), ("treatment", rows)):
        stray = sorted({r["arm"] for r in mine} - {V16_ARM})
        if stray:
            out["invalid"].append("%s file holds unexpected arms %s" % (label, stray))
        shas = {r.get("router_sha") for r in mine}
        if shas != {V16_ROUTERS[label]}:
            out["invalid"].append("%s rows ran on router %s, not %s" % (label, sorted(map(str, shas)), V16_ROUTERS[label]))
    digests = {r.get("root_digest") for r in rows}
    if digests != {V16_ROOT_DIGEST}:
        out["invalid"].append("treatment rows carry root digest %s, not the pinned %s"
                              % (sorted(map(str, digests)), V16_ROOT_DIGEST))
    if any(r.get("named_rules") for r in rows + control):
        out["invalid"].append("a row's prompt named rules files")
    if any(ctx(r).get(k, 0) for r in rows + control for k in ("hint_router", "hint_skill", "linked_table", "hint_label")):
        out["invalid"].append("a row received a depth-hook, index-table or label treatment")
    if any(ctx(r).get("pressure", 0) for r in rows + control):
        out["invalid"].append("a row carries the v15 pressure sentence")
    if any(not ctx(r).get("transcripts") or any(k not in ctx(r) for k in ("rules_lines_seen", "cited_reached", "table_router"))
           for r in rows + control if not excluded(r)):
        out["invalid"].append("a valid row lacks a transcript or the depth/reach fields")
    valid = {}
    for label, mine in (("control", control), ("treatment", rows)):
        valid[label], out["arms"][label] = _arm_stats(mine)
        v = valid[label]
        out["arms"][label].update({
            "code_hint_rate": _rate(v, lambda r: ctx(r).get("hint_code", 0) > 0),
            "table_rate": _rate(v, lambda r: ctx(r).get("table_router", 0) > 0),
            "cited_reached": _rate(v, lambda r: bool(ctx(r).get("cited_reached"))),
            "past_router": _rate(v, lambda r: bool((r.get("depth") or {}).get("past_router"))),
            "mean_rules_read": round(sum((r.get("depth") or {}).get("rules_read", 0) for r in v) / len(v), 2) if v else None,
            "rules_read_errors": sum(ctx(r).get("rules_read_errors", 0) for r in v)})
        if not v:
            out["invalid"].append("%s has no valid rows" % label)
    if valid.get("control") and not sum(_lines(r) for r in valid["control"]):
        out["invalid"].append("the control saw no rules text at all: the relative difference is undefined")
    if out["invalid"]:
        out["verdict"] = "INVALID"
        return out
    manip = {"treatment code_hint_rate": out["arms"]["treatment"]["code_hint_rate"]["rate"] or 0,
             "control table_rate": out["arms"]["control"]["table_rate"]["rate"] or 0,
             "treatment table_rate": out["arms"]["treatment"]["table_rate"]["rate"] or 0}
    if any(v < MANIPULATION_MIN for v in manip.values()):
        out["primary"] = {"verdict": "MANIPULATION FAILED", "manipulation": manip}
        out["verdict"] = "MANIPULATION FAILED"
        return out
    c, t = valid["control"], valid["treatment"]
    out["primary"] = _paired_depth(c, t)
    out["verdict"] = out["primary"]["verdict"]
    keep = lambda vs, drop: [r for r in vs if r["case"] not in drop]
    sec = out["secondary"]
    sec["cited rule tests (v14's primary)"] = dict(_no_verdict(_paired(keep(c, uncited), keep(t, uncited))),
                                                   excluded_uncited_cases=list(uncited))
    sec["all rule tests"] = _no_verdict(_paired(c, t))
    sec["reach of a cited rules file"] = _no_verdict(_paired_reach(c, t))
    sec["past_router"] = {"control": out["arms"]["control"]["past_router"], "treatment": out["arms"]["treatment"]["past_router"]}
    sec["rules-file Reads per run (size-free)"] = {"control": out["arms"]["control"]["mean_rules_read"],
                                                   "treatment": out["arms"]["treatment"]["mean_rules_read"]}
    cc, tc = out["arms"]["control"]["mean_cost_usd"], out["arms"]["treatment"]["mean_cost_usd"]
    sec["cost per run (SDK estimate)"] = {"control": cc, "treatment": tc,
                                          "rel_diff": round((tc - cc) / cc, 3) if cc else None}
    out["compromised"] = any((a["excluded_share"] or 0) > 0.10 for a in out["arms"].values())
    return out


def main(argv=None):
    args = argv or sys.argv[1:]
    if "--v16" in args:     # analyze --v16 <v16 runs.jsonl> <v14 runs.jsonl> <cases-v5/tasks>
        p16, p14, td = [a for a in args if a != "--v16"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v16(load(p16), load(p14), cases_v5_uncited(td)), indent=2, default=str))
        return
    if "--v15" in args:     # analyze --v15 <ctl-pressure runs> <default-pressure runs> <cal-v5 runs> <v14 runs> <cases-v5/tasks>
        a = [x for x in args if x != "--v15"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v15(load(a[0]), load(a[1]), load(a[2]), load(a[3]), cases_v5_uncited(a[4])),
                         indent=2, default=str))
        return
    if "--annotate-reach" in args:   # analyze --annotate-reach <runs.jsonl> <results-dir> <cases.jsonl>
        p, rd, cp = [a for a in args if a != "--annotate-reach"]
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        for r in annotate_reach(rows, rd, cp):
            print(json.dumps(r, default=str))
        return
    if "--v14" in args:     # analyze --v14 <v14 runs.jsonl> <cases-v5 calibration runs.jsonl> <cases-v5/tasks>
        p14, pc, td = [a for a in args if a != "--v14"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v14(load(p14), load(pc), cases_v5_uncited(td)), indent=2))
        return
    if "--v13" in args:     # analyze --v13 <v13 runs.jsonl> <v12 runs re-annotated by --annotate-reach>
        p13, p12 = [a for a in args if a != "--v13"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v13(load(p13), load(p12)), indent=2, default=str))
        return
    if "--v12" in args:     # analyze --v12 <v12 runs.jsonl> <v7 runs annotated by --annotate-reach>
        p12, p7 = [a for a in args if a != "--v12"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v12(load(p12), load(p7)), indent=2, default=str))
        return
    if "--v11" in args:     # analyze --v11 <v11 runs.jsonl> <v10 runs.jsonl> <v9 runs.jsonl>
        p11, p10, p9 = [a for a in args if a != "--v11"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v11(load(p11), load(p10), load(p9)), indent=2, default=str))
        return
    if "--v10" in args:     # analyze --v10 <v10 runs.jsonl> <v9 runs.jsonl> <v7 runs.jsonl>
        p10, p9, p7 = [a for a in args if a != "--v10"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v10(load(p10), load(p9), load(p7)), indent=2, default=str))
        return
    if "--v9" in args:      # analyze --v9 <v9 runs.jsonl> <v7 runs.jsonl> <v8 runs.jsonl>
        p9, p7, p8 = [a for a in args if a != "--v9"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v9(load(p9), load(p7), load(p8)), indent=2, default=str))
        return
    if "--v8" in args:      # analyze --v8 <v8 runs.jsonl> <v7 runs.jsonl>
        p8, p7 = [a for a in args if a != "--v8"]
        load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v8(load(p8), load(p7)), indent=2, default=str))
        return
    if "--v7" in args:      # analyze --v7 <runs.jsonl>
        path = [a for a in args if a != "--v7"][0]
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        print(json.dumps(analyze_v7(rows), indent=2, default=str))
        return
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
