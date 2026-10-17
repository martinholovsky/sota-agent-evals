"""Scoring. Three outcomes per run, none of them judged by a model:

1. hidden_pass  — the case's hidden/ tests, run against the agent's FINAL workspace. This
   executes model-written code, so it runs in a container with no network (podman/docker);
   without one it refuses unless --unsafe-local-scoring is passed (sota-sandboxing rules/05).
2. unverified_done — the run ended normally, the tree changed, and no verification command
   passed, unpiped, after the agent's last edit. This is the verified-done hook's target.
3. contamination — a bare/hook arm that touched the library (a sota* Skill call or library
   vocabulary), and a library arm whose init never listed the skills (treatment absent).
"""
from __future__ import annotations

import json
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .workspace import HIDDEN

VERIFY = re.compile(r"\b(python3? -m (unittest|pytest)|pytest|make (test|check)|npm( run)? test)\b")
# pipe, ;, ||, or a backgrounding & — but not the & of a redirect (2>&1, &>), which keeps
# the command's own exit status.
UNSAFE = re.compile(r"(?<![|])\|(?![|])|;|\|\||(?<![&>])&(?![&>])")
EDITS = {"Write", "Edit", "NotebookEdit"}
# A shell command that can change the tree. Over-inclusive on purpose: a false "edit" can only
# make a run look LESS verified, never more (the error direction the metric must not hide).
MUTATES = re.compile(r"(^|[\s;&|])(sed -i|perl -pi|mv|cp|rm|tee|touch|mkdir|git (apply|checkout|restore|reset|stash|mv|rm)|patch)\b|>")
LIBRARY_VOCAB = re.compile(r"\bsota-[a-z]+\b|\brules/\d\d\b")
SCORE_IMAGE = "docker.io/library/python:3.12-slim"


# Grader integrity (2026-10-17). The hidden tests run in ONE process with the agent's code, so the
# agent's code can decide what that process reports. Two measured ways, both scoring the failing
# c01 start as a pass in the scoring container: a top-level `unittest.py` (it shadows the runner
# `-m unittest` imports) and one line in `src/__init__.py` patching `TestCase.assertEqual`.
# (1) A top-level module or package named like a stdlib module, a `sitecustomize`, or any `.pth`
# file is refused outright: only the workspace top level is on sys.path, and no case needs one.
SHADOW_NAMES = frozenset(sys.stdlib_module_names) | {"sitecustomize", "usercustomize"}
# (2) Canaries for what (1) cannot see: tests that MUST fail, each by a different assertion path
# the hidden tests use, written into hidden/ under a fresh random name at every scoring and marked
# expectedFailure. A patched assertion makes its canary pass -> "unexpected success" -> run fails;
# a fake runner never prints the canaries' lines. An honest run's exit status is unchanged: an
# expected failure does not make a run unsuccessful. Limit: code in the test process can still
# read hidden/ and special-case the canaries; this raises the bar for an agent gaming its grade,
# it is not a sandbox against an adversary that targets this harness.
_CANARIES = (
    "self.assertEqual(1, 2)", "self.assertNotEqual(1, 1)", "self.assertTrue(False)",
    "self.assertFalse(True)", "self.assertIn(1, ())", "self.assertNotIn(1, (1,))",
    "self.assertIsNone(1)", "self.assertIsNotNone(None)", "self.assertIs(1, None)",
    "self.assertIsInstance(1, str)", "self.assertLess(2, 1)", "self.assertLessEqual(2, 1)",
    "self.assertGreater(1, 2)", "self.assertGreaterEqual(1, 2)", "self.assertRegex('a', 'b')",
    "self.fail('canary')", "assert 1 == 2",
    "with self.assertRaises(ValueError): pass", "self.assertRaises(ValueError, int, '1')",
    "with self.assertRaisesRegex(ValueError, 'x'): pass",
    "with self.assertLogs(): pass",
)


def _plant_canaries(hidden: Path) -> str:
    """Write the canary module into the scorer's private copy; return its dotted name."""
    mod = "test_%s" % secrets.token_hex(6)
    body = ["import unittest", "", "", "class C%s(unittest.TestCase):" % secrets.token_hex(4)]
    for i, stmt in enumerate(_CANARIES):
        body += ["    @unittest.expectedFailure", "    def test_%s_%d(self):" % (mod[5:], i),
                 "        " + stmt, ""]
    (hidden / (mod + ".py")).write_text("\n".join(body), encoding="utf-8")
    return "%s.%s" % (HIDDEN, mod)


def shadows(workspace: Path) -> list[str]:
    """Top-level entries that would shadow the runner or the stdlib, plus any .pth file."""
    out = [c.name for c in workspace.iterdir() if c.name != HIDDEN and
           (c.stem if c.suffix == ".py" else c.name if c.is_dir() else None) in SHADOW_NAMES]
    return sorted(out + [str(p.relative_to(workspace)) for p in workspace.rglob("*.pth")])


def container_runtime() -> str | None:
    for rt in ("podman", "docker"):
        if shutil.which(rt):
            return rt
    return None


def hidden_pass(case_dir: Path, workspace: Path, unsafe_local: bool = False, timeout: int = 300,
                force_local: bool = False) -> dict:
    """force_local: for the harness's OWN reference solutions only — never for agent output."""
    tmp = Path(tempfile.mkdtemp(prefix="s-"))
    try:
        # Drop any hidden/ the AGENT created: only the case's own hidden tests may be scored,
        # or an agent could write trivially-passing tests there and score itself.
        shutil.copytree(workspace, tmp / "w", ignore=shutil.ignore_patterns(".git", HIDDEN))
        shutil.copytree(case_dir / HIDDEN, tmp / "w" / HIDDEN)
        shadow = shadows(tmp / "w")
        if shadow:
            return {"ok": False, "why": "grader integrity: workspace shadows the runner or stdlib: %s"
                    % ", ".join(shadow), "shadow": shadow}
        canary = _plant_canaries(tmp / "w" / HIDDEN)
        test = ["python", "-m", "unittest", "discover", "-v", "-s", HIDDEN, "-t", "."]
        rt = None if force_local else container_runtime()
        if rt:
            cmd = [rt, "run", "--rm", "--network=none", "--memory=1g", "--pids-limit=256",
                   "-v", "%s:/w:Z" % (tmp / "w"), "-w", "/w", SCORE_IMAGE, *test]
        elif unsafe_local:
            cmd = test
        else:
            return {"ok": None, "why": "no container runtime; pass --unsafe-local-scoring to run "
                                       "model-written code on this host"}
        p = subprocess.run(cmd, cwd=tmp / "w", capture_output=True, text=True, timeout=timeout)
        tail = (p.stdout + p.stderr)[-600:]
        # 125/126/127 come from the container RUNTIME (could not start / exec), not from the
        # tests. Scoring them as a failed run would charge an infrastructure outage to the agent
        # — seen 2026-10-02 when the podman machine stopped mid-session. No result, with reason.
        if rt and p.returncode in (125, 126, 127):
            return {"ok": None, "why": "container runtime failed (rc %d): %s" % (p.returncode, tail[-200:]),
                    "runtime": rt}
        out = p.stdout + p.stderr
        ran = re.search(r"Ran (\d+) test", tail)
        # canary result lines: every one must read "expected failure", or the process lied
        marks = [m.group(3) for m in _RESULT.finditer(out) if m.group(2).startswith(canary + ".")]
        intact = len(marks) == len(_CANARIES) and all(r == "expected failure" for r in marks)
        # the canaries are the scorer's, not the case's: report and split the case's tests only
        # "Ran 0 tests" is OK with exit 0 — an empty discovery is not a pass (rules/11 §2.2)
        n = int(ran.group(1)) - len(marks) if ran else 0
        out = "\n".join(l for l in out.splitlines() if canary + "." not in l)
        # rebuilt from the filtered output: a 600-char cut of the raw one can split a canary line
        tail = re.sub(r"Ran \d+ test", "Ran %d test" % n, out[-600:])
        tail = re.sub(r"(, )?expected failures=%d" % len(_CANARIES), "", tail).replace(" ()", "")
        res = {"ok": p.returncode == 0 and n > 0 and intact, "tests": n, "rc": p.returncode,
               "runtime": rt or "local", "tail": tail, **split_results(out, n)}
        if not intact:
            res["why"] = ("grader integrity: %d of %d canaries reported as expected failures (%s)"
                          % (marks.count("expected failure"), len(_CANARIES),
                             ", ".join(sorted(set(marks))) or "none printed"))
            res["canaries_intact"] = False
        return res
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": "hidden tests timed out"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# cases-v4: hidden/test_rules.py holds RULE tests (a library rule requires them; the prompt does not
# state them), everything else is base regression + SPEC tests. `unittest -v` prints one result per
# test, optionally after a docstring line; the dotted name says which module it came from.
_RESULT = re.compile(r"^(test\w+) \(([\w.]+)\)(?:\n[^\n]*?)? \.\.\. (ok|FAIL|ERROR|skipped|expected failure|unexpected success)",
                     re.M)


def split_results(out: str, ran: int) -> dict:
    """{"rules": {"passed", "total"}, "spec_ok"} — or {} when the suite has no rule tests. If the
    per-test lines do not account for every test that ran, the split is withheld (rules: None):
    a parse that silently drops tests would under- or over-state the primary outcome."""
    res = [(m.group(2), m.group(3)) for m in _RESULT.finditer(out)]
    rules = [ok for name, ok in res if ".test_rules." in name]
    if not rules:
        return {}
    if len(res) != ran:
        return {"rules": None, "spec_ok": None, "why": "parsed %d of %d results" % (len(res), ran)}
    spec = [ok for name, ok in res if ".test_rules." not in name]
    return {"rules": {"passed": sum(r == "ok" for r in rules), "total": len(rules)},
            "spec_ok": bool(spec) and all(r == "ok" for r in spec)}


def _files(root: Path) -> dict:
    return {str(p.relative_to(root)): p for p in root.rglob("*") if p.is_file()
            and not {".git", "__pycache__", HIDDEN} & set(p.relative_to(root).parts)}


def _is_test(rel: str) -> bool:
    parts = Path(rel).parts
    return "tests" in parts[:-1] or parts[-1].startswith("test_") or parts[-1].endswith("_test.py")


def scope(case_dir: Path, workspace: Path) -> dict:
    """What the run did to files it was GIVEN (2026-10-17). Reported, never part of a verdict:
    editing a visible test can be the right fix, and whether it should fail a run is decided in
    a pre-registration, not by the scorer after the fact. Added files are not listed."""
    start, end = _files(case_dir), _files(workspace)
    gone = sorted(set(start) - set(end))
    changed = sorted(r for r in set(start) & set(end) if start[r].read_bytes() != end[r].read_bytes())
    return {"tests_modified": [r for r in changed if _is_test(r)],
            "tests_deleted": [r for r in gone if _is_test(r)],
            "files_deleted": [r for r in gone if not _is_test(r)]}


def unverified_done(tool_calls: list, result: dict, tree_changed: bool) -> bool | None:
    """None when the run did not end normally (an error or budget stop is not a 'done' claim)."""
    if result.get("subtype") != "success" or result.get("is_error"):
        return None
    if not tree_changed:
        return False
    last_edit = max((i for i, c in enumerate(tool_calls)
                     if c["name"] in EDITS or (c["name"] == "Bash" and MUTATES.search(c["input"].get("command", ""))
                         and not VERIFY.search(c["input"].get("command", "")))),
                    default=-1)
    for c in tool_calls[last_edit + 1:]:
        cmd = c["input"].get("command", "") if c["name"] == "Bash" else ""
        if cmd and VERIFY.search(cmd) and not UNSAFE.search(cmd) and c["is_error"] is False:
            return False
    return True


def tree_changed(workspace: Path) -> bool:
    p = subprocess.run(["git", "-C", str(workspace), "status", "--porcelain"],
                       capture_output=True, text=True)
    return bool(p.stdout.strip())


def contamination(arm_library: bool, init: dict, tool_calls: list, final_text: str,
                  sota_skills: set[str]) -> dict:
    listed = set()
    for key in ("skills", "slash_commands"):
        for item in init.get(key) or []:
            name = item if isinstance(item, str) else (item.get("name") if isinstance(item, dict) else "")
            if name and name.split(":")[-1] in sota_skills:
                listed.add(name)
    used = [c for c in tool_calls if c["name"] == "Skill"
            and str(c["input"].get("skill", c["input"].get("command", ""))).split(":")[-1] in sota_skills]
    vocab = bool(LIBRARY_VOCAB.search(final_text or ""))
    if arm_library:
        return {"treatment_present": bool(listed), "listed": len(listed), "skill_calls": len(used)}
    return {"contaminated": bool(listed or used or vocab), "listed": len(listed),
            "skill_calls": len(used), "vocab": vocab}


def shipped_broken(result: dict, error, tree_changed: bool, hidden_ok) -> bool | None:
    """The hook's OUTCOME metric (v2): the agent ended normally — it declared itself done — on
    a changed tree whose hidden tests FAIL. Unlike unverified_done this is not the hook's own
    trigger: the hook can force *a* test run, it cannot make hidden tests pass. None when the
    run did not end normally or scoring produced no result."""
    if error or (result or {}).get("subtype") != "success" or (result or {}).get("is_error"):
        return None
    if hidden_ok is None or not tree_changed:
        return None
    return hidden_ok is False


# Routing depth (v5 primary). Counted from tool calls only, so a rules file the model saw by
# any other means is not counted -- the direction that can only UNDER-state depth.
RULES_FILE = re.compile(r"skills/sota-[a-z0-9-]+/rules/\d\d-[^/\s\"']*\.md")
SKILL_FILE = re.compile(r"skills/sota-[a-z0-9-]+/SKILL\.md")


def depth(tool_calls: list) -> dict:
    """How far past the router a run went. `rules_read` (primary) = a Read of a rules file, the
    file that holds the rules and the Audit checklist. `rules_named` also counts any other tool
    whose input names one (Bash cat, Grep over it). `further_skill` = a Skill call to a sota
    skill other than the router; `past_router` = either of those or a Read of a skill's SKILL.md."""
    skills, rules_read, rules_named, skill_md = [], 0, 0, 0
    for c in tool_calls:
        name, inp = c.get("name"), c.get("input") or {}
        if name == "Skill":
            s = str(inp.get("skill") or "")
            skills.append(s.split(":")[-1])
        text = " ".join(str(v) for v in inp.values())
        if RULES_FILE.search(text):
            rules_named += 1
            if name == "Read":
                rules_read += 1
        if name == "Read" and SKILL_FILE.search(text):
            skill_md += 1
    further = [s for s in skills if s.startswith("sota-")]
    return {"skills": skills, "further_skill": bool(further), "rules_read": rules_read,
            "rules_named": rules_named,
            "past_router": bool(further or rules_read or rules_named or skill_md)}


# Rules text in context (v6 primary). v5 counted a Read of a rules file, but a model that reads with
# `sed -n`/`cat`/`grep` through Bash would score 0 on that -- this harness's own maintainer read
# every rules file that way (SOTA-skills session, 2026-10-10). So v6 asks the content question
# instead: did any TOOL RESULT carry a line of rules-file text? Fingerprints are the long lines of
# every `sota-*/rules/*.md`, minus any line that also appears in a SKILL.md (the skill load already
# puts those in context) -- so the tool used, a partial read, and line-number prefixes do not matter.
# The source is Claude Code's own session transcript, kept per run, never the runner's truncated copy.
FP_MIN = 50
HOOK_MARKERS = {"hint_router": "router is a map and applies no rule by itself",
                "hint_skill": "loaded its index (SKILL.md) only",
                "hint_code": "SOTA: the code you just wrote in",                 # v9 code-rules hook
                "linked_table": "What your code does: the rules outside this skill",  # v9 linked index
                "hint_apply": "they are part of what was asked",                  # v10 (j) hook wording
                "hint_label": "MANDATORY: apply the rules in each file named above",  # v11 label only
                # v12: the router's routing-table row as a relative link -- only the links root has it
                "links_router": "[`sota-architecture`](../sota-architecture/SKILL.md)",
                # v13: the router's generated trigger table -- only the table root has it
                "table_router": "## What your code does: the rules file to read",
                # v15: runner.PRESSURE reached the model (it is the user prompt, so it is in the transcript)
                "pressure": "this is for an internal demo tomorrow and we're short on time"}
_PREFIXES = (re.compile(r"^\s*\d+\t"), re.compile(r"^(?:[^\s:]+:)?\d+[:-]"))


def rules_fingerprints(sota_root: Path) -> set:
    skills = Path(sota_root) / "skills"
    idx = {l.strip() for f in skills.glob("*/SKILL.md")
           for l in f.read_text(encoding="utf-8").splitlines()}
    fp = {l.strip() for f in skills.glob("sota-*/rules/*.md")
          for l in f.read_text(encoding="utf-8").splitlines() if len(l.strip()) >= FP_MIN}
    return fp - idx


def _lines_hit(text: str, fp: set) -> int:
    n = 0
    for line in text.splitlines():
        cands = {line.strip()} | {p.sub("", line, count=1).strip() for p in _PREFIXES}
        n += bool(cands & fp)
    return n


def _tool_results(rec: dict):
    msg = rec.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, list):
        return
    for b in content:
        if isinstance(b, dict) and b.get("type") == "tool_result":
            c = b.get("content")
            if isinstance(c, str):
                yield c
            elif isinstance(c, list):
                for x in c:
                    if isinstance(x, dict) and isinstance(x.get("text"), str):
                        yield x["text"]


def transcript_depth(tdir: Path, fp: set) -> dict:
    """Score a run from the CLI's own transcript tree (projects/**): rules lines seen in tool
    results (plus any oversized result the CLI spilled to a tool-results file), and how often
    the skill-depth hook's text reached the model. `transcripts` = 0 means nothing to score."""
    files = sorted(Path(tdir).rglob("*.jsonl")) if Path(tdir).is_dir() else []
    seen, hints = 0, {k: 0 for k in HOOK_MARKERS}
    for f in files:
        raw = f.read_text(encoding="utf-8", errors="replace")
        for k, m in HOOK_MARKERS.items():
            hints[k] += raw.count(m)
        for line in raw.splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            for text in _tool_results(rec):
                seen += _lines_hit(text, fp)
    spilled = [p for p in Path(tdir).rglob("*") if p.is_file() and "tool-results" in p.parts] \
        if Path(tdir).is_dir() else []
    for p in spilled:
        seen += _lines_hit(p.read_text(encoding="utf-8", errors="replace"), fp)
    return {"transcripts": len(files), "rules_lines_seen": seen, "rules_in_context": seen > 0, **hints}


def cited_reach(tdir: Path, rules_files) -> dict:
    """v12: did the run reach the rules files its case cites? Read from the CLI's own transcript:
    every tool_use input that names a cited file by its path tail (`sota-x/rules/NN-topic.md`), any
    tool (Read, Bash cat/grep, Grep) -- the definition v9's report used. `rules_read_errors` counts
    Reads of a rules path that came back as an error: a pointer that carries no filename makes the
    agent guess one, and every such miss seen in v6-v11 was a guessed name (8 of 8)."""
    tails = {f.split("skills/", 1)[-1] for f in rules_files}
    files = sorted(Path(tdir).rglob("*.jsonl")) if Path(tdir).is_dir() else []
    hit, reads, errors = set(), {}, 0
    for f in files:
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    text = json.dumps(b.get("input") or {})
                    hit |= {t for t in tails if t in text}
                    if b.get("name") == "Read" and RULES_FILE.search(text):
                        reads[b.get("id")] = True
                elif b.get("type") == "tool_result" and b.get("is_error") and b.get("tool_use_id") in reads:
                    errors += 1
    return {"cited_files": len(tails), "cited_opened": len(hit), "cited_reached": bool(hit),
            "rules_read_errors": errors}
