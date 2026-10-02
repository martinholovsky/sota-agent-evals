"""Harness tests — the instrument is a control too (SOTA-skills sota-code-security rules/15).
Each scorer is shown a known-good AND a known-bad input; isolation is checked in both
directions. No API key and no SDK are needed."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from agent_evals import arms as A
from agent_evals.runner import RunConfig, options_for
from agent_evals.score import contamination, hidden_pass, unverified_done
from agent_evals.workspace import HIDDEN, load_cases, make_workspace

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "cases"
REFS = Path(__file__).resolve().parent / "references"


@pytest.fixture(scope="session")
def fake_sota(tmp_path_factory):
    """A minimal SOTA-skills shape: two skills and the hook script path."""
    r = tmp_path_factory.mktemp("lib")
    for n in ("sota", "sota-shell-scripting"):
        (r / "skills" / n).mkdir(parents=True)
        (r / "skills" / n / "SKILL.md").write_text("---\nname: %s\ndescription: x\n---\n" % n)
    (r / "scripts").mkdir()
    (r / "scripts" / "verified-done-hook.py").write_text("")
    return r


# ---- cases ------------------------------------------------------------------------------
def test_cases_header_declares_selection_rule():
    head = json.loads((CASES / "cases.jsonl").read_text().splitlines()[0])
    assert "selection_rule" in head and head["set_type"] in ("instrument", "measurement")


@pytest.mark.parametrize("case", load_cases(CASES), ids=lambda c: c.id)
def test_case_is_solvable_and_not_presolved(case):
    """Reference passes the hidden tests; the untouched start fails them. A case nobody can
    pass, or that passes untouched, measures nothing."""
    start = hidden_pass(case.dir, case.dir, unsafe_local=True, force_local=True)
    assert start["ok"] is False, start
    ws = Path(tempfile.mkdtemp())
    try:
        shutil.copytree(case.dir, ws, dirs_exist_ok=True, ignore=shutil.ignore_patterns(HIDDEN))
        shutil.copytree(REFS / case.id, ws, dirs_exist_ok=True)
        solved = hidden_pass(case.dir, ws, unsafe_local=True, force_local=True)
        assert solved["ok"] is True and solved["tests"] > 0, solved
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_hidden_pass_rejects_zero_tests(tmp_path):
    """'Ran 0 tests' exits 0 — an empty discovery must not read as a pass."""
    case = tmp_path / "c"; (case / HIDDEN).mkdir(parents=True); (case / HIDDEN / "__init__.py").write_text("")
    ws = tmp_path / "w"; ws.mkdir()
    r = hidden_pass(case, ws, unsafe_local=True, force_local=True)
    assert r["ok"] is False and r["tests"] == 0


# ---- workspace isolation ----------------------------------------------------------------
def test_workspace_never_contains_hidden_tests_or_references():
    for case in load_cases(CASES):
        ws = make_workspace(case)
        try:
            names = {p.name for p in ws.rglob("*")}
            assert HIDDEN not in names and "references" not in names
            assert "sota" not in str(ws).lower()
            assert subprocess.run(["git", "-C", str(ws), "status", "--porcelain"],
                                  capture_output=True, text=True).stdout == ""
        finally:
            shutil.rmtree(ws, ignore_errors=True)


@pytest.mark.parametrize("arm", list(A.ARMS.values()), ids=lambda a: a.name)
def test_arm_config_is_isolated_and_symmetric(arm, fake_sota):
    case = load_cases(CASES)[0]
    ws, cd, kw = options_for(arm, case, RunConfig(model="m", sota_root=fake_sota), "k")
    try:
        assert kw["setting_sources"] == ["user"]
        assert kw["env"]["CLAUDE_CONFIG_DIR"] == str(cd)
        assert kw["env"]["HOME"].startswith(str(cd)) and not any((cd / "home").iterdir())
        for v in ("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "ENABLE_CLAUDEAI_MCP_SERVERS",
                  "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"):
            assert v in kw["env"]
        assert kw["sandbox"]["failIfUnavailable"] is True
        assert kw["sandbox"]["allowUnsandboxedCommands"] is False
        assert kw["permission_mode"] == "dontAsk"
        skills = {p.name for p in (cd / "skills").iterdir()}
        assert skills == ({"sota", "sota-shell-scripting"} if arm.library else set())
        settings = json.loads((cd / "settings.json").read_text())
        assert ("hooks" in settings) == arm.hook
        if arm.hook:
            assert set(settings["hooks"]) == {"SessionStart", "PostToolUse", "PostToolUseFailure", "Stop"}
        for p in (str(ws), str(cd)):
            assert "sota" not in p.lower() and arm.name not in p
    finally:
        A.cleanup(ws, cd)


# ---- unverified_done --------------------------------------------------------------------
def bash(cmd, err=False):
    return {"name": "Bash", "input": {"command": cmd}, "is_error": err}


EDIT = {"name": "Edit", "input": {"file_path": "x"}, "is_error": False}
OK = {"subtype": "success", "is_error": False}
UT = "python3 -m unittest discover -s tests -t ."


@pytest.mark.parametrize("calls,changed,want", [
    ([EDIT, bash(UT)], True, False),                       # edit then passing run
    ([EDIT, bash(UT + " 2>&1")], True, False),             # 2>&1 keeps the exit status
    ([EDIT, bash(UT), bash("ls -la")], True, False),       # a read after the run is not an edit
    ([EDIT], True, True),                                  # nothing run
    ([EDIT, bash(UT + " | tail -3")], True, True),         # piped: tail's status
    ([EDIT, bash(UT, err=True)], True, True),              # failing run
    ([EDIT, bash(UT), EDIT], True, True),                  # edit after the passing run
    ([EDIT, bash(UT), bash("sed -i s/a/b/ f")], True, True),  # shell edit after the run
    ([], False, False),                                    # nothing changed
])
def test_unverified_done(calls, changed, want):
    assert unverified_done(calls, OK, changed) is want


def test_unverified_done_is_none_when_run_did_not_finish():
    assert unverified_done([EDIT], {"subtype": "error_max_turns", "is_error": True}, True) is None


# ---- contamination ----------------------------------------------------------------------
SK = {"sota", "sota-shell-scripting"}


def test_contamination_both_directions():
    clean = contamination(False, {"skills": []}, [bash("ls")], "done", SK)
    assert clean["contaminated"] is False
    assert contamination(False, {}, [{"name": "Skill", "input": {"skill": "sota"}, "is_error": False}],
                         "", SK)["contaminated"] is True
    assert contamination(False, {}, [], "per sota-shell-scripting rules/06", SK)["contaminated"] is True
    assert contamination(False, {"skills": ["sota"]}, [], "", SK)["contaminated"] is True
    assert contamination(True, {"skills": ["sota-shell-scripting"]}, [], "", SK)["treatment_present"] is True
    assert contamination(True, {"skills": []}, [], "", SK)["treatment_present"] is False


def test_agent_written_hidden_dir_cannot_score_itself(tmp_path):
    """Known-bad: the agent plants hidden/ with a passing test; the CASE's tests must be used."""
    case = load_cases(CASES)[0]
    ws = make_workspace(case)
    try:
        (ws / HIDDEN).mkdir()
        (ws / HIDDEN / "__init__.py").write_text("")
        (ws / HIDDEN / "test_hidden.py").write_text(
            "import unittest\nclass X(unittest.TestCase):\n    def test_x(self): pass\n")
        assert hidden_pass(case.dir, ws, unsafe_local=True, force_local=True)["ok"] is False
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_preflight_fails_on_errored_runs(tmp_path):
    """Known-bad from the first live run: two 401s, no init, and the gate printed PASS."""
    from agent_evals.cli import check_preflight
    rows = tmp_path / "p.jsonl"
    err = {"error": "ResultError: 401", "init_seen": False, "result": {},
           "contamination": {"listed": 0, "treatment_present": False}}
    rows.write_text("\n".join(json.dumps(dict(err, arm=a)) for a in ("bare", "library")) + "\n")
    assert check_preflight(rows) == 1
    ok = {"error": None, "init_seen": True, "result": {"subtype": "success"}}
    rows.write_text(json.dumps(dict(ok, arm="bare", contamination={"listed": 0})) + "\n" +
                    json.dumps(dict(ok, arm="library", contamination={"listed": 42, "treatment_present": True})) + "\n")
    assert check_preflight(rows) == 0


# ---- the concurrent runner, end to end with a fake SDK call -----------------------------
def _fake_run_one(cost):
    async def fake(arm, case, sample, cfg, key):
        from agent_evals.runner import Trace, options_for
        ws, cd, _ = options_for(arm, case, cfg, key)
        tr = Trace(case.id, arm.name, sample, init={"skills": []},
                   result={"subtype": "success", "is_error": False, "total_cost_usd": cost})
        return ws, cd, tr
    return fake


def _args(tmp_path, fake_sota, **kw):
    import argparse
    d = dict(model="m", sota_root=fake_sota, cases=CASES, only=None, arms="bare,library",
             samples=2, max_turns=5, max_budget_usd=1.0, total_budget_usd=100.0, timeout=60,
             out=str(tmp_path / "out"), unsafe_local_scoring=True, concurrency=3, provider="anthropic")
    d.update(kw)
    return argparse.Namespace(**d)


def test_runner_runs_every_job_once(tmp_path, fake_sota, monkeypatch):
    from agent_evals import cli
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(cli, "run_one", _fake_run_one(0.01))
    assert cli.cmd_run(_args(tmp_path, fake_sota)) == 0
    rows = [json.loads(l) for l in (tmp_path / "out" / "runs.jsonl").read_text().splitlines()]
    keys = {(r["case"], r["arm"], r["sample"]) for r in rows}
    assert len(rows) == len(keys) == len(load_cases(CASES)) * 2 * 2   # cases x arms x samples
    kept = list((tmp_path / "out" / "workspaces").iterdir())
    assert len(kept) == len(rows)                      # every final workspace kept for re-scoring


def test_runner_stops_at_total_budget(tmp_path, fake_sota, monkeypatch):
    """Known-bad: a budget that is never enforced. $0.50/run against a $1.00 cap, one at a time."""
    from agent_evals import cli
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(cli, "run_one", _fake_run_one(0.50))
    cli.cmd_run(_args(tmp_path, fake_sota, total_budget_usd=1.0, concurrency=1))
    rows = (tmp_path / "out" / "runs.jsonl").read_text().splitlines()
    assert len(rows) == 2


# ---- the pre-registered analysis, on synthetic rows with a known answer -----------------
def _rows(spec):
    """spec: {arm: (hidden_ok_prob_by_case_fn, unverified_fn)} -> rows over 20 cases x 3 samples."""
    rows = []
    for arm, (hp, ud) in spec.items():
        for i in range(20):
            for s in range(3):
                rows.append({"case": "c%02d" % i, "arm": arm, "sample": s, "error": None,
                             "hidden": {"ok": hp(i, s)}, "unverified_done": ud(i, s),
                             "contamination": {"contaminated": False} if "library" not in arm
                             else {"treatment_present": True}})
    return rows


def test_analysis_detects_a_real_effect_and_not_a_null():
    from agent_evals.analyze import analyze
    effect = _rows({"bare": (lambda i, s: i % 2 == 0, lambda i, s: True),
                    "hook": (lambda i, s: i % 2 == 0, lambda i, s: False),
                    "library": (lambda i, s: True, lambda i, s: True),
                    "library+hook": (lambda i, s: True, lambda i, s: False)})
    v = {h["name"]: h["verdict"] for h in analyze(effect)["hypotheses"]}
    assert v["H1a hook vs bare"] == "SUPPORTED" and v["H2 library vs bare"] == "SUPPORTED"
    null = _rows({a: (lambda i, s: i % 2 == 0, lambda i, s: i % 3 == 0)
                  for a in ("bare", "hook", "library", "library+hook")})
    v = {h["name"]: h["verdict"] for h in analyze(null)["hypotheses"]}
    assert v["H1a hook vs bare"] == "NOT SUPPORTED" and v["H2 library vs bare"] == "NOT SUPPORTED"


def test_analysis_excludes_and_counts_contaminated_rows():
    from agent_evals.analyze import analyze
    rows = _rows({"bare": (lambda i, s: True, lambda i, s: False)})
    rows[0]["contamination"] = {"contaminated": True}
    rows[1]["error"] = "timeout"
    out = analyze(rows)
    assert out["excluded"] == {"contaminated:bare": 1, "error:bare": 1}


def test_runtime_failure_is_no_result_not_a_failed_run(tmp_path, monkeypatch):
    """Known-bad from 2026-10-02: podman down -> rc 125 was scored as the AGENT failing."""
    from agent_evals import score
    case = load_cases(CASES)[0]
    monkeypatch.setattr(score, "container_runtime", lambda: "false")   # `false` exits 1...
    class P:  # ...so fake the runtime's own 125 directly
        returncode, stdout, stderr = 125, "", "Error: unable to connect to Podman socket"
    monkeypatch.setattr(score.subprocess, "run", lambda *a, **k: P())
    r = score.hidden_pass(case.dir, case.dir)
    assert r["ok"] is None and "runtime failed" in r["why"]


def test_openrouter_env_and_key_not_left_in_process(monkeypatch):
    from agent_evals import cli
    from agent_evals.arms import run_env
    env = run_env(Path(tempfile.mkdtemp()), "or-key", "openrouter", "anthropic/claude-sonnet-5.5")
    assert env["ANTHROPIC_BASE_URL"] == "https://openrouter.ai/api"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "or-key" and env["ANTHROPIC_API_KEY"] == ""
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "anthropic/claude-sonnet-5.5"
    assert env["CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"] == "1"
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    assert cli._key(True, "openrouter") == "or-key"
    import os
    assert "OPENROUTER_API_KEY" not in os.environ          # popped: the agent cannot inherit it


def test_analysis_excludes_hook_arm_where_hook_never_ran():
    from agent_evals.analyze import excluded
    assert excluded({"arm": "hook", "hook_ledger": False, "contamination": {}}) == "hook-treatment-mismatch"
    assert excluded({"arm": "bare", "hook_ledger": True, "contamination": {}}) == "hook-treatment-mismatch"
    assert excluded({"arm": "hook", "hook_ledger": True, "contamination": {}}) is None
