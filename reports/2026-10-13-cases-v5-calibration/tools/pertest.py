"""Per-rule-test results for cases-v5 workspaces, through the harness's own container command.

  python pertest.py overlays            # control: every reference passes, every naive fails, per test
  python pertest.py RUN_DIR             # RUN_DIR/workspaces/<case>__<arm>__<s>
Prints one JSON line per workspace and pooled all / cited / cited-minus-weak rates.
"""
import json, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path.home() / "Github/sota-agent-evals"))
from agent_evals.score import SCORE_IMAGE, _RESULT, container_runtime

CASES = Path.home() / "Github/sota-agent-evals/cases-v5"
WEAK = {"w01", "w15", "w18"}
RULES = {c.name: json.loads((c / "rules.json").read_text()) for c in sorted((CASES / "tasks").iterdir())}

def per_test(case, ws):
    tmp = Path(tempfile.mkdtemp(prefix="s-"))
    try:
        shutil.copytree(ws, tmp / "w", ignore=shutil.ignore_patterns(".git", "hidden"))
        shutil.copytree(CASES / case / "hidden", tmp / "w" / "hidden")
        rt = container_runtime()
        assert rt, "no container runtime"
        p = subprocess.run([rt, "run", "--rm", "--network=none", "--memory=1g", "--pids-limit=256",
                            "-v", "%s:/w:Z" % (tmp / "w"), "-w", "/w", SCORE_IMAGE,
                            "python", "-m", "unittest", "discover", "-v", "-s", "hidden", "-t", "."],
                           capture_output=True, text=True, timeout=300)
        out = p.stdout + p.stderr
        ran = int((re.search(r"Ran (\d+) test", out) or [0, 0])[1])
        res = {(m.group(2), m.group(1)): m.group(3) for m in _RESULT.finditer(out)}
        if len(res) != ran or ran == 0:
            return {"case": case, "error": "parsed %d of %d" % (len(res), ran)}
        rules = {name: ok == "ok" for (mod, name), ok in res.items() if ".test_rules." in mod}
        spec_ok = all(ok == "ok" for (mod, _), ok in res.items() if ".test_rules." not in mod)
        want = {e["test"] for e in RULES[case]}
        if set(rules) != want:
            return {"case": case, "error": "rule tests %s != rules.json %s" % (sorted(rules), sorted(want))}
        return {"case": case, "spec_ok": spec_ok, "rules": rules}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def pooled(rows):
    def rate(pred):
        v = [ok for r in rows if "rules" in r for e in RULES[r["case"]] if pred(r["case"], e)
             for ok in [r["rules"][e["test"]]]]
        return "%d/%d" % (sum(v), len(v))
    return {"all": rate(lambda c, e: True), "cited": rate(lambda c, e: "quote" in e),
            "cited_minus_weak": rate(lambda c, e: "quote" in e and c not in WEAK)}

def main():
    jobs = []
    if sys.argv[1] == "overlays":
        for c in RULES:
            for kind in ("reference", "naive"):
                ws = Path(tempfile.mkdtemp(prefix="w-"))
                shutil.copytree(CASES / c, ws, dirs_exist_ok=True, ignore=shutil.ignore_patterns("hidden"))
                shutil.copytree(CASES / "tasks" / c / kind, ws, dirs_exist_ok=True)
                jobs.append((c, ws, kind))
    else:
        for ws in sorted((Path(sys.argv[1]) / "workspaces").iterdir()):
            jobs.append((ws.name.split("__")[0], ws, ws.name))
    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(lambda j: dict(per_test(j[0], j[1]), label=j[2]), jobs))
    for r in rows:
        print(json.dumps(r))
    errs = [r for r in rows if "error" in r]
    print("workspaces %d, errors %d" % (len(rows), len(errs)))
    if sys.argv[1] == "overlays":
        for kind in ("reference", "naive"):
            print(kind, pooled([r for r in rows if r["label"] == kind]))
    else:
        print("pooled", pooled(rows), "spec_ok", sum(r.get("spec_ok") is True for r in rows), "of", len(rows))

main()
