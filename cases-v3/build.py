#!/usr/bin/env python3
"""Assemble cases-v3 from base/ + tasks/<id>/, and verify each task.

tasks/<id>/ holds:
  prompt.md              the task, as given to the agent (the only task text it sees)
  start/   (optional)    files overlaid on base/ to form the starting repo (e.g. a planted bug)
  visible/ (optional)    extra test files added under tests/ in the starting repo
  hidden/test_task.py    hidden tests for this task (imports `hidden.helpers`, never `tests.*`)
  reference/             files overlaid on the starting repo that solve the task

Built case dir (cases-v3/<id>/) = base + start + visible, plus hidden/ = a PRISTINE copy of the
base suite (imports rewritten to hidden.*) + the task's hidden tests. Scoring runs hidden/, so an
agent cannot pass by editing the visible tests, and every task is also scored on the full
regression suite of the base application.

  python3 cases-v3/build.py            # build all + write cases-v3/cases.jsonl
  python3 cases-v3/build.py --verify   # build, then check every task (see verify())
  python3 cases-v3/build.py --verify t07 t08   # only these tasks (cases.jsonl untouched)
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
BASE, TASKS = HERE / "base", HERE / "tasks"
HEADER = {
    "purpose": "MEASUREMENT SET v3: tasks against one multi-module application; hidden scoring = the full base regression suite + task tests",
    "selection_rule": "authored 2026-10-02 before any v3 run, from a fixed list of 20 change tasks spanning features, security, refactors and planted-bug fixes against cases-v3/base; every hidden assertion follows from prompt.md or base/README.md; reviewed by an independent spec reader before freezing. Never selected, edited or dropped by observed model performance.",
    "set_type": "measurement",
}


def overlay(src: pathlib.Path, dst: pathlib.Path):
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def build_one(tid: str) -> pathlib.Path:
    t = TASKS / tid
    out = HERE / tid
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(BASE, out)
    overlay(t / "start", out)
    overlay(t / "visible", out / "tests")
    hid = out / "hidden"
    hid.mkdir()
    (hid / "__init__.py").write_text("")
    for f in (BASE / "tests").glob("*.py"):
        if f.name == "__init__.py":
            continue
        (hid / f.name).write_text(f.read_text().replace("from tests.", "from hidden.")
                                  .replace("import tests.", "import hidden."))
    shutil.copy(t / "hidden" / "test_task.py", hid / "test_task.py")
    return out


def run_hidden(repo: pathlib.Path, pattern: str = "test*.py"):
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "hidden", "-t", ".",
                        "-p", pattern], cwd=repo, capture_output=True, text=True, timeout=300)
    return p.returncode, (p.stdout + p.stderr)[-1500:]


def verify(tid: str) -> list:
    """Problems with a task, empty if it is sound:
    - the starting repo passes the base regression suite (unless the task plants a bug),
    - the starting repo FAILS the task's hidden tests (not pre-solved),
    - the reference passes the base suite AND the task's hidden tests (solvable)."""
    case = build_one(tid)
    probs = []
    planted = (TASKS / tid / "start").is_dir()
    rc, out = run_hidden(case, "test_[!t]*.py")          # base suite only (not test_task.py)
    if rc != 0 and not planted:
        probs.append("start fails the base suite:\n" + out)
    rc, out = run_hidden(case, "test_task.py")
    if rc == 0:
        probs.append("start already passes test_task.py (pre-solved)")
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        shutil.copytree(case, tmp / "r")
        overlay(TASKS / tid / "reference", tmp / "r")
        rc, out = run_hidden(tmp / "r")
        if rc != 0 or "Ran 0 tests" in out:
            probs.append("reference fails hidden (base + task):\n" + out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return probs


def main():
    ids = sorted(p.name for p in TASKS.iterdir() if (p / "prompt.md").exists())
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    if only:                      # build/verify just these, and leave cases.jsonl alone, so
        ids = [i for i in ids if i in only]   # parallel authors cannot clobber each other
    else:
        rows = [HEADER] + [{"id": tid, "prompt": (TASKS / tid / "prompt.md").read_text().strip()}
                           for tid in ids]
        (HERE / "cases.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    for tid in ids:
        build_one(tid)
    print("built %d cases" % len(ids))
    if "--verify" in sys.argv:
        bad = 0
        for tid in ids:
            probs = verify(tid)
            bad += bool(probs)
            print("%s %s" % (tid, "OK" if not probs else "BAD"))
            for p in probs:
                print("   " + p.replace("\n", "\n   "))
        print("verify: %d of %d tasks have problems" % (bad, len(ids)))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
