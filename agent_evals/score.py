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
import shutil
import subprocess
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
        ran = re.search(r"Ran (\d+) test", tail)
        # "Ran 0 tests" is OK with exit 0 — an empty discovery is not a pass (rules/11 §2.2)
        n = int(ran.group(1)) if ran else 0
        return {"ok": p.returncode == 0 and n > 0, "tests": n, "rc": p.returncode,
                "runtime": rt or "local", "tail": tail, **split_results(p.stdout + p.stderr, n)}
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
                "hint_skill": "loaded its index (SKILL.md) only"}
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
