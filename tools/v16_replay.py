#!/usr/bin/env python3
"""v16 offline replay (PRE-REGISTRATION-v16.md). No model calls, no network: it reads v14's kept
transcripts and two `git archive` roots of SOTA-skills, and prints what can be predicted about the
treatment's depth before any v16 run.

    python3 tools/v16_replay.py results/v14-2026-10-13 <root 4a5fee40> <root origin/main>

1. Instrument drift. Every v14 transcript is re-scored with score.transcript_depth() against the
   fingerprints of each root and of their union. Against the old root it must reproduce the
   `rules_lines_seen` v14 recorded (the positive control); against today's root it shows how much
   of the same text still matches verbatim after the edits.
2. Size only. For the rules files each v14 run Read, the fingerprint lines those files hold in each
   root. If agents read the same files in full on today's root, depth moves by this factor with no
   change in routing.
3. Hook naming. Each v14 code edit (Edit/Write/MultiEdit, the hook's own path gates) is replayed in
   order through each root's code-rules-hook `select()`, with the once-per-session rule, against that
   root's skills/. Under the old root the files it names must equal the files the real hook named
   in the transcript (second positive control).

Limits: agents under today's library may write other code and read other files; this predicts the
hook's naming and the size effect, not the run.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_evals.score import RULES_FILE, rules_fingerprints, transcript_depth  # noqa: E402

NAMED = re.compile(r"Its rules: \S+?/skills/(sota-[a-z0-9-]+/rules/\d\d-[^\s]+?\.md) \(")


def load_hook(root: Path):
    spec = importlib.util.spec_from_file_location("crh_%d" % id(root), root / "scripts" / "code-rules-hook.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # resolve skills inside THIS root only, never the operator's ~/.claude or CLAUDE_CONFIG_DIR
    mod.skill_dir = lambda name: (root / "skills" / name) if (root / "skills" / name / "SKILL.md").is_file() else None
    return mod


def tool_uses(tdir: Path):
    seen = set()
    for f in sorted(tdir.rglob("*.jsonl")):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            content = (rec.get("message") or {}).get("content")
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in seen:
                    seen.add(b.get("id"))
                    yield b


def hook_named_in_transcript(tdir: Path) -> set:
    raw = "".join(f.read_text(encoding="utf-8", errors="replace") for f in tdir.rglob("*.jsonl"))
    raw = raw.replace("\\n", "\n").replace('\\"', '"')
    return set(NAMED.findall(raw))


def replay_hook(mod, edits: list) -> set:
    already, named = set(), set()
    scratch = getattr(mod, "SCRATCH_PATH", None)
    config_ext = getattr(mod, "CONFIG_EXT", set())
    for b in edits:
        ti = b.get("input") or {}
        path = str(ti.get("file_path") or "")
        ext = path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
        if ext in mod.CODE_EXT:
            rows = None
        elif ext in config_ext:
            rows = mod.CONFIG_ROWS
        else:
            continue
        if mod.TEST_PATH.search(path) or (scratch and scratch.search(path)):
            continue
        args = (mod.written_text(ti), already) + ((rows,) if config_ext else ())
        for _what, p, _sec in mod.select(*args):
            already.add(str(p))
            named.add(str(p).split("/skills/", 1)[-1])
    return named


def fp_lines(path: Path, fp: set) -> int:
    if not path.is_file():
        return 0
    return sum(1 for l in path.read_text(encoding="utf-8").splitlines() if l.strip() in fp)


def main():
    res_dir, root_a, root_b = (Path(x) for x in sys.argv[1:4])
    rows = {r["case"]: r for r in (json.loads(l) for l in open(res_dir / "runs.jsonl", encoding="utf-8") if l.strip())}
    fp_a, fp_b = rules_fingerprints(root_a), rules_fingerprints(root_b)
    fp_u = fp_a | fp_b
    # lines of sota-shell-scripting rules files (either root): today's routing block in CLAUDE.md
    # names three of them, so their share is reported apart (PRE-REGISTRATION-v16, descriptive)
    fp_sh = {l.strip() for root in (root_a, root_b) for f in root.glob("skills/sota-shell-scripting/rules/*.md")
             for l in f.read_text(encoding="utf-8").splitlines()} & fp_u
    print("fingerprints: 4a5fee40 %d, origin/main %d, shared %d, union %d"
          % (len(fp_a), len(fp_b), len(fp_a & fp_b), len(fp_u)))
    tot_a = sum(fp_lines(p, fp_a) for p in root_a.glob("skills/sota-*/rules/*.md"))
    tot_b = sum(fp_lines(p, fp_b) for p in root_b.glob("skills/sota-*/rules/*.md"))
    print("fingerprint lines in all rules files: %d -> %d (x%.3f)" % (tot_a, tot_b, tot_b / tot_a))
    hook_a, hook_b = load_hook(root_a), load_hook(root_b)
    print("\ncase  recorded  vs_a  vs_b  vs_union | files_read size_a size_b | hook_a hook_b real==replay_a shell  only_b")
    agg = {"rec": 0, "a": 0, "b": 0, "u": 0, "sa": 0, "sb": 0, "ok": 0, "n": 0, "na": 0, "nb": 0, "sh": 0}
    newly = {}
    for case in sorted(rows):
        r = rows[case]
        tdir = res_dir / "transcripts" / ("%s__%s__%d" % (case, r["arm"].replace("+", "_"), r["sample"]))
        rec = (r.get("context") or {}).get("rules_lines_seen")
        da, db, du = (transcript_depth(tdir, fp)["rules_lines_seen"] for fp in (fp_a, fp_b, fp_u))
        sh = transcript_depth(tdir, fp_sh)["rules_lines_seen"]
        uses = list(tool_uses(tdir))
        read = sorted({m.group(0).split("skills/", 1)[-1] for b in uses if b.get("name") == "Read"
                       for m in [RULES_FILE.search(str((b.get("input") or {}).get("file_path") or ""))] if m})
        sa = sum(fp_lines(root_a / "skills" / f, fp_a) for f in read)
        sb = sum(fp_lines(root_b / "skills" / f, fp_b) for f in read)
        edits = [b for b in uses if b.get("name") in ("Edit", "Write", "MultiEdit")]
        na, nb = replay_hook(hook_a, edits), replay_hook(hook_b, edits)
        real = hook_named_in_transcript(tdir)
        ok = real == na
        newly[case] = sorted(nb - na)
        print("%-5s %8s %5d %5d %8d | %10d %6d %6d | %6d %6d %14s %5d  %s"
              % (case, rec, da, db, du, len(read), sa, sb, len(na), len(nb), ok, sh, ", ".join(newly[case]) or "-"))
        for k, v in (("rec", rec or 0), ("a", da), ("b", db), ("u", du), ("sa", sa), ("sb", sb),
                     ("ok", ok), ("n", 1), ("na", len(na)), ("nb", len(nb)), ("sh", sh)):
            agg[k] += v
    print("\ntotals: recorded %d; re-scored vs 4a5fee40 %d, vs origin/main %d (%.1f%%), vs union %d"
          % (agg["rec"], agg["a"], agg["b"], 100 * agg["b"] / agg["a"], agg["u"]))
    print("size only (same files read in full): %d -> %d fingerprint lines (x%.3f)"
          % (agg["sa"], agg["sb"], agg["sb"] / agg["sa"]))
    print("hook replay: files named %d (4a5fee40) -> %d (origin/main); replay matches the real hook in %d/%d runs; "
          "runs where today's hook names a file the old one did not: %d"
          % (agg["na"], agg["nb"], agg["ok"], agg["n"], sum(1 for v in newly.values() if v)))
    print("lines from sota-shell-scripting rules files (union fingerprints): %d of %d (%.1f%%)"
          % (agg["sh"], agg["u"], 100 * agg["sh"] / max(agg["u"], 1)))
    print("mean per run: recorded %.1f; size-only prediction %.1f"
          % (agg["rec"] / agg["n"], agg["rec"] / agg["n"] * agg["sb"] / agg["sa"]))


if __name__ == "__main__":
    main()
