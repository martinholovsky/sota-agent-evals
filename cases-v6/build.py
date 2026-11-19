#!/usr/bin/env python3
"""Assemble cases-v6 from base/ + tasks/<id>/, and verify each task.

cases-v6 is a SENTINEL set. It reuses cases-v5's shop (base/ is a byte-for-byte copy) and
cases-v5's verification machinery unchanged, but inverts what the second test file measures.
In every task a careful engineer would NOT add one particular security or robustness control,
and adding it is the mistake:

  s01  explicit prohibition       the prompt forbids a control and gives a reason that holds here
  s02  a genuine design decision  the prompt leaves a security decision to an owner who has not
                                  made it; correct is to build what is decidable and ask
  s03  a declared, scoped prototype  the prompt authorises omitting one named control
  s04  control already enforced   an existing, base-tested layer already decides it; a second
                                  copy diverges and breaks a legitimate caller

tasks/<id>/ holds:
  prompt.md               the task as given to the agent (the only task text it sees)
  start/   (optional)     files overlaid on base/ to form the starting repo
  hidden/test_task.py     SPEC tests: the feature the prompt asks for works
                          (import `hidden.helpers`, never `tests.*`)
  hidden/test_rules.py    SENTINEL tests: the behaviour that respects the request holds (the
                          forbidden or unneeded control is absent, or the decision was not made
                          unilaterally)
  asvs.txt                the task's sentinel id, SENTINEL-<id> (no ASVS requirement applies)
  rules.json              [{"test": "<sentinel test method name>", "asvs": "SENTINEL-<id>"}]
  reference/              overlay that solves the task AND respects the sentinel
  naive/                  the OVER-BUILDER: solves the task AND adds the control it should not
  AUTHOR-NOTES.md         the sentinel, what correct looks like, what the final message should
                          say, accepted variants, weaknesses

verify(<id>) requires (logic unchanged from cases-v5; "rule" below means "sentinel"):
  1. start passes the base regression suite
  2. start FAILS test_task.py                         (not pre-solved)
  3. reference passes base + test_task + test_rules   (solvable while respecting the sentinel)
  4. naive passes base + test_task                    (the over-builder meets the spec ...)
  5. naive fails EVERY test in test_rules.py          (... and each sentinel test detects it)
  6a. every test in test_rules.py maps to the task's own id in asvs.txt
  6b (--cited) is inherited from cases-v5 and does not apply: sentinel tests carry no citation.
Not mechanised: that the final message says what AUTHOR-NOTES.md asks for (stated reason,
question asked, omission disclosed, no claimed control). A test file cannot read the message.

  python3 cases-v6/build.py                  # build all + write cases.jsonl
  python3 cases-v6/build.py --verify         # checks 1-5 and 6a
  python3 cases-v6/build.py --verify s01 s03
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
BASE, TASKS = HERE / "base", HERE / "tasks"
HEADER = {
    "purpose": "SENTINEL SET v6: four tasks against the cases-v5 shop application in which a careful engineer would NOT add a particular security or robustness control (explicit prohibition, an undecided design decision, a declared scoped prototype, a control already enforced by an existing layer). Hidden SPEC tests check the feature; hidden SENTINEL tests check that the over-built control is absent or the decision was left open.",
    "selection_rule": "Four hand-authored tasks, one per sentinel kind, written blind to every hook and detector. build.py --verify proves for every task that an over-builder solution meeting the prompt fails every sentinel test and a reference that respects the request passes them.",
    "set_type": "sentinel",
}


def overlay(src: pathlib.Path, dst: pathlib.Path):
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))


def build_one(tid: str) -> pathlib.Path:
    t = TASKS / tid
    out = HERE / tid
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(BASE, out, ignore=shutil.ignore_patterns("__pycache__"))
    overlay(t / "start", out)
    hid = out / "hidden"
    hid.mkdir()
    (hid / "__init__.py").write_text("")
    for f in (BASE / "tests").glob("*.py"):
        if f.name == "__init__.py":
            continue
        (hid / f.name).write_text(f.read_text().replace("from tests.", "from hidden.")
                                  .replace("import tests.", "import hidden."))
    for name in ("test_task.py", "test_rules.py"):
        shutil.copy(t / "hidden" / name, hid / name)
    return out


def run_hidden(repo: pathlib.Path, pattern: str = "test*.py"):
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-v", "-s", "hidden", "-t",
                        ".", "-p", pattern], cwd=repo, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout + p.stderr


RESULT = re.compile(r"^(test\w+) \([\w.]+\)(?:\n.*?)? \.\.\. (ok|FAIL|ERROR|skipped.*)$", re.M)


def per_test(out: str) -> dict:
    """{test method: 'ok'|'FAIL'|'ERROR'|'skipped'} from `unittest -v` output."""
    return {m.group(1): m.group(2).split()[0] for m in RESULT.finditer(out)}


def rule_test_names(tid: str) -> list:
    src = (TASKS / tid / "hidden" / "test_rules.py").read_text()
    return re.findall(r"^\s+def (test\w+)\(", src, re.M)


def norm(s: str) -> str:
    return " ".join(s.split())


def check_citations(tid: str, sota_root, cited: bool) -> list:
    probs = []
    cites = json.loads((TASKS / tid / "rules.json").read_text())
    asvs = (TASKS / tid / "asvs.txt").read_text().strip()
    names = set(rule_test_names(tid))
    have = {c["test"] for c in cites}
    for n in sorted(names - have):
        probs.append("rule test %s has no rules.json entry" % n)
    for n in sorted(have - names):
        probs.append("rules.json entry for %s, which is not a test in test_rules.py" % n)
    for c in cites:
        if c.get("asvs") != asvs:                                   # 6a
            probs.append("%s: maps to %r, not the task's ASVS id %s" % (c["test"], c.get("asvs"), asvs))
        if not cited:
            continue
        if "uncited" in c:                                          # 6b
            if "file" in c or len(c["uncited"].strip()) < 20:
                probs.append("%s: 'uncited' must stand alone and name the searches tried" % c["test"])
            continue
        f = sota_root / c.get("file", "")
        if not re.fullmatch(r"skills/sota-[a-z0-9-]+/rules/\d\d-[\w-]+\.md", c.get("file", "")):
            probs.append("%s: cites %r, not a sota-* rules file" % (c["test"], c.get("file")))
        elif not f.is_file():
            probs.append("%s: cited file %s does not exist" % (c["test"], c["file"]))
        elif len(norm(c.get("quote", ""))) < 30 or norm(c["quote"]) not in norm(f.read_text()):
            probs.append("%s: quote not found verbatim in %s: %r" % (c["test"], c["file"], c.get("quote", "")[:90]))
    return probs


def verify(tid: str, sota_root, cited: bool) -> list:
    case = build_one(tid)
    probs = []
    # v4 plants no bugs: start/ only adds existing interface (a documented seam, a helper), so the
    # starting repo must ALWAYS pass the base suite. (v3 skipped this check whenever start/ existed.)
    rc, out = run_hidden(case, "test_[!tr]*.py")          # base suite only
    if rc != 0 or "Ran 0 tests" in out:
        probs.append("start fails the base suite:\n" + out[-1500:])
    rc, out = run_hidden(case, "test_task.py")
    if rc == 0:
        probs.append("start already passes test_task.py (pre-solved)")
    names = rule_test_names(tid)
    if not names:
        probs.append("test_rules.py defines no tests")
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        for which in ("reference", "naive"):
            r = tmp / which
            shutil.copytree(case, r)
            overlay(TASKS / tid / which, r)
            rc_spec, out_spec = run_hidden(r, "test_[!r]*.py")      # base + test_task
            rc_rule, out_rule = run_hidden(r, "test_rules.py")
            if which == "reference":
                if rc_spec != 0 or "Ran 0 tests" in out_spec:
                    probs.append("reference fails base/spec tests:\n" + out_spec[-1500:])
                if rc_rule != 0:
                    probs.append("reference fails rule tests:\n" + out_rule[-1500:])
            else:
                if rc_spec != 0 or "Ran 0 tests" in out_spec:
                    probs.append("naive fails base/spec tests (the spec alone must be satisfiable):\n"
                                 + out_spec[-1500:])
                res = per_test(out_rule)
                missing = [n for n in names if n not in res]
                if missing:
                    probs.append("could not read naive results for %s:\n%s" % (missing, out_rule[-800:]))
                passed = [n for n in names if res.get(n) == "ok"]
                if passed:
                    probs.append("naive PASSES rule tests %s -- they do not test the rule" % passed)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    probs += check_citations(tid, sota_root, cited)
    return probs


def main():
    args = sys.argv[1:]
    cited = "--cited" in args
    sota_root = None
    if "--sota-root" in args:
        i = args.index("--sota-root")
        sota_root = pathlib.Path(args[i + 1]).expanduser().resolve()
        del args[i:i + 2]
    if cited and sota_root is None:
        raise SystemExit("--cited needs --sota-root PATH (citations are checked against it)")
    ids = sorted(p.name for p in TASKS.iterdir() if (p / "prompt.md").exists())
    only = [a for a in args if not a.startswith("--")]
    if only:
        ids = [x for x in ids if x in only]
    else:
        # rules_files: the library rules files a task's cited RULE tests name (empty before the
        # citation pass). Read only by an `installed+named`-style arm; every other arm ignores it.
        rows = [HEADER] + [{"id": tid, "asvs": (TASKS / tid / "asvs.txt").read_text().strip(),
                            "prompt": (TASKS / tid / "prompt.md").read_text().strip(),
                            "rules_files": sorted({c["file"] for c in
                                                   json.loads((TASKS / tid / "rules.json").read_text())
                                                   if "file" in c})}
                           for tid in ids]
        (HERE / "cases.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    for tid in ids:
        build_one(tid)
    print("built %d cases" % len(ids))
    if "--verify" in args:
        bad = 0
        for tid in ids:
            probs = verify(tid, sota_root, cited)
            bad += bool(probs)
            print("%s %s (%d rule tests)" % (tid, "OK" if not probs else "BAD", len(rule_test_names(tid))))
            for p in probs:
                print("   " + p.replace("\n", "\n   "))
        print("verify%s: %d of %d tasks have problems" % (" --cited" if cited else "", bad, len(ids)))
        return 1 if bad or not ids else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
