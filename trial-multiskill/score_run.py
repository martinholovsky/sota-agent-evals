#!/usr/bin/env python3
"""Score one trial run folder with the frozen hidden tests (verify.py's runner, unchanged).

Usage: score_run.py <run-folder> [<run-folder> ...]

For each folder: copy it to a temp dir (no .git, caches or databases), put hidden/ beside it, run
all hidden tests in-process as verify.py does, and run the agent's own tests with
`python -m unittest discover -s tests`. Prints spec and rule pass counts, each failing test, and
the agent's own test result. Never writes into the run folder.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify  # noqa: E402  the frozen runner and the expected test list


def score(folder: Path) -> dict:
    expected = verify.expected_tests()
    with tempfile.TemporaryDirectory(prefix="docket-score-") as tmp:
        work = Path(tmp) / folder.name
        shutil.copytree(folder, work, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "*.pyc", "*.db", "*.sqlite*", ".venv", "files"))
        if (work / "hidden").exists():
            raise SystemExit("%s already has a hidden/ directory; refusing to overwrite it" % folder)
        shutil.copytree(verify.HIDDEN, work / "hidden", ignore=shutil.ignore_patterns("__pycache__"))
        t0 = time.monotonic()
        proc = subprocess.run([sys.executable, "-c", verify.RUNNER], cwd=work, capture_output=True,
                              text=True, timeout=1800)
        hidden_s = time.monotonic() - t0
        payload = {"outcome": {}, "ran": 0, "load_errors": ["no result line: runner crashed"]}
        for line in proc.stdout.splitlines():
            if line.startswith("@@RESULTS@@"):
                payload = json.loads(line[len("@@RESULTS@@"):])
        results = {}
        for test_id, status in payload["outcome"].items():
            parts = test_id.split(".")
            if len(parts) == 4 and parts[0] == "hidden":
                results[(parts[1], parts[3])] = status
        shutil.rmtree(work / "hidden")
        own = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=work,
                             capture_output=True, text=True, timeout=900) if (work / "tests").is_dir() else None
    out = {"folder": str(folder), "hidden_seconds": round(hidden_s, 1), "load_errors": payload["load_errors"]}
    for kind, names in expected.items():
        got = {t: results.get((kind, t), "NOT RUN") for t in names}
        out[kind] = {"passed": sum(s == "ok" for s in got.values()), "total": len(names),
                     "failing": {t: s for t, s in got.items() if s != "ok"}}
    if own is None:
        out["own_tests"] = "no tests/ directory"
    else:
        tail = [l for l in own.stderr.splitlines() if l.startswith(("Ran ", "OK", "FAILED"))]
        out["own_tests"] = {"exit": own.returncode, "summary": " | ".join(tail)}
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(2)
    for arg in sys.argv[1:]:
        print(json.dumps(score(Path(arg).resolve()), indent=1))
