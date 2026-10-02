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
        test = ["python", "-m", "unittest", "discover", "-s", HIDDEN, "-t", "."]
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
                "runtime": rt or "local", "tail": tail}
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": "hidden tests timed out"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
