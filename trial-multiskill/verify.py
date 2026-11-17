#!/usr/bin/env python3
"""Run the hidden tests against each solution in an isolated temp copy.

For each of reference/ and naive/: copy the solution to a fresh temp dir, copy
hidden/ beside it, and run the equivalent of `python -m unittest discover -s
hidden -t .` there (network is never needed; outcomes come back as JSON), then
assert:

  * reference passes every spec test and every rule test;
  * naive passes every spec test;
  * naive's rule-test results are reported (not asserted);
  * a deny-all negative control (reference admin/migrations, an app that
    refuses every request) passes ZERO rule tests, i.e. the rule tests fail
    closed instead of reading a refusal as a protection.

Exit status 0 only if every assertion holds. Standard library only.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"
# Runs inside the temp copy: the same discovery as
# `python -m unittest discover -s hidden -t .`, but outcomes come back as JSON
# instead of being scraped from verbose text (log lines interleave with it).
RUNNER = r"""
import json, logging, sys, unittest
logging.getLogger().addHandler(logging.NullHandler())  # keep stderr readable
class R(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.outcome = {}
    def _set(self, test, status):
        key = test.id()
        if self.outcome.get(key) in ("FAIL", "ERROR"):
            return
        self.outcome[key] = status
    def addSuccess(self, t): super().addSuccess(t); self.outcome.setdefault(t.id(), "ok")
    def addFailure(self, t, e): super().addFailure(t, e); self._set(t, "FAIL")
    def addError(self, t, e):
        super().addError(t, e); self._set(t, "ERROR")
    def addSkip(self, t, r): super().addSkip(t, r); self._set(t, "skipped")
    def addSubTest(self, t, st, e):
        super().addSubTest(t, st, e)
        if e is not None:
            self._set(t, "FAIL" if issubclass(e[0], t.failureException) else "ERROR")
suite = unittest.defaultTestLoader.discover("hidden", top_level_dir=".")
runner = unittest.TextTestRunner(resultclass=R, verbosity=1, stream=sys.stderr)
res = runner.run(suite)
print("@@RESULTS@@" + json.dumps({"outcome": res.outcome, "ran": res.testsRun,
      "load_errors": [str(e) for e in getattr(unittest.defaultTestLoader, "errors", [])]}))
sys.exit(0 if res.wasSuccessful() else 1)
"""


def expected_tests():
    """Count test methods statically so a crash that stops discovery cannot
    shrink the denominator."""
    out = {}
    for kind in ("test_spec", "test_rules"):
        src = (HIDDEN / f"{kind}.py").read_text()
        out[kind] = sorted(set(re.findall(r"^    def (test_\w+)\(self\)", src, re.M)))
    return out


# Negative control for "rule tests fail closed": the reference's admin helpers and
# migrations with an app that refuses every request and never delivers. Every
# rule test must FAIL against it; a pass would mean a test reads "refused" as
# "protected" without checking the feature exists.
DENY_ALL_APP = '''"""Negative control: every request refused, no deliveries."""
import time
from . import db


class Deny:
    def __init__(self, db_path):
        db.migrate(db_path)

    def __call__(self, environ, start_response):
        start_response("403 Forbidden", [("Content-Type", "application/json")])
        return [b'{"error": "forbidden"}']

    def run_pending_deliveries(self):
        return 0

    def start_worker(self, interval=1.0):
        pass

    def stop_worker(self):
        pass


def create_app(db_path, *, clock=time.time, http_post=None, resolve=None):
    return Deny(db_path)
'''


def run_solution(name):
    src = HERE / ("reference" if name == "deny-all" else name)
    with tempfile.TemporaryDirectory(prefix=f"docket-verify-{name}-") as tmp:
        work = Path(tmp) / name
        shutil.copytree(src, work, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.db"))
        if name == "deny-all":
            (work / "docket" / "app.py").write_text(DENY_ALL_APP)
        shutil.copytree(HIDDEN, work / "hidden", ignore=shutil.ignore_patterns("__pycache__"))
        t0 = time.monotonic()
        proc = subprocess.run([sys.executable, "-c", RUNNER], cwd=work, capture_output=True,
                              text=True, timeout=1800)
        elapsed = time.monotonic() - t0
    results = {}
    payload = {"outcome": {}, "ran": 0, "load_errors": ["no result line: runner crashed"]}
    for line in proc.stdout.splitlines():
        if line.startswith("@@RESULTS@@"):
            payload = json.loads(line[len("@@RESULTS@@"):])
    for test_id, status in payload["outcome"].items():
        parts = test_id.split(".")  # hidden.<module>.<Class>.<method>
        if len(parts) == 4 and parts[0] == "hidden":
            results[(parts[1], parts[3])] = status
    proc.payload = payload
    return proc, results, elapsed


def summarise(name, proc, results, elapsed, expected):
    print(f"=== {name}: unittest exit {proc.returncode}, {elapsed:.1f}s")
    tail = [l for l in proc.stderr.splitlines() if l.startswith(("Ran ", "OK", "FAILED"))]
    print("    " + " | ".join(tail) + f" | ran {proc.payload['ran']} | load errors: {proc.payload['load_errors'] or 'none'}")
    summary = {}
    for kind, names in expected.items():
        got = {t: results.get((kind, t), "NOT RUN") for t in names}
        passed = [t for t, s in got.items() if s == "ok"]
        summary[kind] = got
        print(f"    {kind}: {len(passed)}/{len(names)} passed")
        for t, s in got.items():
            if s != "ok":
                print(f"      {s:8} {t}")
    return summary


def main():
    expected = expected_tests()
    print(f"hidden tests: {len(expected['test_spec'])} spec, {len(expected['test_rules'])} rule")
    failures = []
    report = {}
    for name in ("reference", "naive", "deny-all"):
        proc, results, elapsed = run_solution(name)
        report[name] = summarise(name, proc, results, elapsed, expected)
        if name == "reference" and proc.returncode != 0:
            print(proc.stderr[-6000:])
    ref, naive = report["reference"], report["naive"]
    for kind in ("test_spec", "test_rules"):
        bad = [t for t, s in ref[kind].items() if s != "ok"]
        if bad:
            failures.append(f"reference fails {kind}: {bad}")
    bad = [t for t, s in naive["test_spec"].items() if s != "ok"]
    if bad:
        failures.append(f"naive fails spec tests: {bad}")
    naive_rule_pass = [t for t, s in naive["test_rules"].items() if s == "ok"]
    deny_rule_pass = [t for t, s in report["deny-all"]["test_rules"].items() if s == "ok"]
    if deny_rule_pass:
        failures.append(f"rule tests pass against the deny-all control (not fail-closed): {deny_rule_pass}")
    print("=== summary")
    print(f"reference: spec {sum(s == 'ok' for s in ref['test_spec'].values())}/{len(ref['test_spec'])},"
          f" rules {sum(s == 'ok' for s in ref['test_rules'].values())}/{len(ref['test_rules'])}")
    print(f"naive:     spec {sum(s == 'ok' for s in naive['test_spec'].values())}/{len(naive['test_spec'])},"
          f" rules {len(naive_rule_pass)}/{len(naive['test_rules'])}"
          f" (rule tests naive passes: {naive_rule_pass or 'none'})")
    print(f"deny-all control: rules passed {len(deny_rule_pass)}/{len(report['deny-all']['test_rules'])}"
          f" (must be 0: rule tests fail closed)")
    if failures:
        for f in failures:
            print("ASSERTION FAILED:", f)
        return 1
    print("ALL ASSERTIONS HOLD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
