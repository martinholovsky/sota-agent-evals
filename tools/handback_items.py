#!/usr/bin/env python3
"""ROADMAP 73 (l): build one item per FAILED rule test, with the run's final message.

Each item: run set, case, arm, sample, the failed test's name and docstring (the risk it checks,
which a final message would have to name to have "handed it back"), and the run's final text.
Labelling is a separate step; this only assembles what a labeller reads.

A combined run set (vN-DATE) whose halves vN-DATE-a and vN-DATE-b also exist is skipped: it
repeats their runs. A test's risk is its own docstring, else the module docstring (cases-v4).

Failed test names come from the hidden-test output tail. The tail is truncated, so when it names
fewer tests than failed, the run is resolved only if EVERY rule test of the case failed (then the
names are the case's whole test_rules.py); otherwise it is reported as unresolvable, never guessed.

Usage: handback_items.py <results-dir> <repo-root> > items.jsonl   (summary on stderr)
"""
import ast, glob, json, os, re, sys

CASESET = {  # run-set prefix -> case set its tasks came from (checked below against test names)
    "v7": "cases-v4", "v8": "cases-v4", "v9": "cases-v4", "v10": "cases-v4", "v11": "cases-v4",
    "v12": "cases-v4", "v13": "cases-v4", "v14": "cases-v5", "v15": "cases-v5", "v16": "cases-v5",
}


def rule_tests(root, caseset, case):
    p = os.path.join(root, caseset, case, "hidden", "test_rules.py")
    if not os.path.exists(p):
        return {}
    tree = ast.parse(open(p, encoding="utf-8").read())
    module_doc = (ast.get_docstring(tree) or "").strip()  # cases-v4 states the rule here, not per test
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
            out[n.name] = (ast.get_docstring(n) or "").strip() or module_doc
    return out


def main(results, root):
    items, stats = [], {"runs_with_failures": 0, "resolved_runs": 0, "unresolvable_runs": 0,
                        "no_final_text": 0, "name_not_in_case": 0}
    for f in sorted(glob.glob(os.path.join(results, "*", "runs.jsonl"))):
        d = os.path.basename(os.path.dirname(f))
        if any(x in d for x in ("pilot", "gates", "preflight", "measurement")) or d.startswith("cal-"):
            continue
        if os.path.isdir(os.path.join(results, d + "-a")):
            continue  # a combined set that only repeats its -a and -b halves
        prefix = d.split("-")[0]
        if prefix not in CASESET:
            continue
        traces = os.path.join(os.path.dirname(f), "traces")
        for line in open(f, encoding="utf-8"):
            if not line.strip():
                continue
            o = json.loads(line)
            r = (o.get("hidden") or {}).get("rules") or {}
            total, failed = r.get("total") or 0, (r.get("total") or 0) - (r.get("passed") or 0)
            if failed <= 0:
                continue
            stats["runs_with_failures"] += 1
            tests = rule_tests(root, CASESET[prefix], o["case"])
            tail = o["hidden"].get("tail", "")
            named = set(re.findall(r"(?:FAIL|ERROR): (test_\w+)", tail)) | set(re.findall(r"in (test_\w+)\n", tail))
            named &= set(tests)
            if len(named) >= failed:
                names = sorted(named)
            elif tests and failed == total == len(tests):
                names = sorted(tests)
            else:
                stats["unresolvable_runs"] += 1
                continue
            stats["resolved_runs"] += 1
            tf = os.path.join(traces, f"{o['case']}__{o['arm'].replace('+', '_')}__{o['sample']}.json")
            final = ""
            if os.path.exists(tf):
                final = json.load(open(tf, encoding="utf-8")).get("final_text") or ""
            if not final:
                stats["no_final_text"] += 1
            for n in names:
                items.append({"run_set": d, "case": o["case"], "arm": o["arm"], "sample": o["sample"],
                              "test": n, "risk": tests.get(n, ""), "final_text": final})
    for it in items:
        print(json.dumps(it))
    stats["items"] = len(items)
    print(json.dumps(stats), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
