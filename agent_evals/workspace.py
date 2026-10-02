"""Cases and their disposable workspaces.

A case directory holds the starting repo plus a `hidden/` directory of tests the agent never
sees. The workspace is a COPY without `hidden/` — if hidden tests leaked into the workspace the
agent could read the answer, and every arm would score high for a reason unrelated to the
treatment. `tests/test_workspace.py` asserts that, as a known-bad.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

HIDDEN = "hidden"


@dataclass(frozen=True)
class Case:
    id: str
    dir: Path
    prompt: str


def load_cases(cases_dir: Path, only: list[str] | None = None) -> list[Case]:
    """cases.jsonl: line 1 is a header object declaring the SELECTION RULE; then one case per line."""
    lines = (cases_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    if "selection_rule" not in header or "purpose" not in header:
        raise SystemExit("cases.jsonl header must declare selection_rule and purpose")
    cases = []
    for l in lines[1:]:
        if not l.strip():
            continue
        c = json.loads(l)
        d = cases_dir / c["id"]
        if not (d / HIDDEN).is_dir():
            raise SystemExit("case %s has no hidden/ tests — it cannot be scored" % c["id"])
        cases.append(Case(c["id"], d, c["prompt"]))
    if only:
        cases = [c for c in cases if c.id in only]
    if not cases:
        raise SystemExit("0 cases selected — refusing to report on an empty run")
    return cases


def make_workspace(case: Case) -> Path:
    """Copy the case minus hidden/, as a git repo with one commit (the verified-done hook keys
    on git tree ids). Prefix `w-`: no arm or library name may appear in a path the agent sees."""
    ws = Path(tempfile.mkdtemp(prefix="w-"))
    shutil.copytree(case.dir, ws, dirs_exist_ok=True, ignore=shutil.ignore_patterns(HIDDEN))
    for args in (["init", "-q"], ["config", "user.email", "agent@example.invalid"],
                 ["config", "user.name", "agent"], ["add", "-A"], ["commit", "-qm", "start"]):
        subprocess.run(["git", "-C", str(ws), *args], check=True, capture_output=True)
    return ws
