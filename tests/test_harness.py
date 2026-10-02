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
    assert "selection_rule" in head and head["set_type"] == "instrument"


@pytest.mark.parametrize("case", load_cases(CASES), ids=lambda c: c.id)
def test_case_is_solvable_and_not_presolved(case):
    """Reference passes the hidden tests; the untouched start fails them. A case nobody can
    pass, or that passes untouched, measures nothing."""
    start = hidden_pass(case.dir, case.dir, unsafe_local=True)
    assert start["ok"] is False, start
    ws = Path(tempfile.mkdtemp())
    try:
        shutil.copytree(case.dir, ws, dirs_exist_ok=True, ignore=shutil.ignore_patterns(HIDDEN))
        shutil.copytree(REFS / case.id, ws, dirs_exist_ok=True)
        solved = hidden_pass(case.dir, ws, unsafe_local=True)
        assert solved["ok"] is True and solved["tests"] > 0, solved
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_hidden_pass_rejects_zero_tests(tmp_path):
    """'Ran 0 tests' exits 0 — an empty discovery must not read as a pass."""
    case = tmp_path / "c"; (case / HIDDEN).mkdir(parents=True); (case / HIDDEN / "__init__.py").write_text("")
    ws = tmp_path / "w"; ws.mkdir()
    r = hidden_pass(case, ws, unsafe_local=True)
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
        assert hidden_pass(case.dir, ws, unsafe_local=True)["ok"] is False
    finally:
        shutil.rmtree(ws, ignore_errors=True)
