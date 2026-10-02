"""Command line: dry-run (no API), preflight (isolation controls, cents), run (a measurement).

    python -m agent_evals dry-run   --sota-root ~/Github/SOTA-skills
    python -m agent_evals preflight --sota-root ~/Github/SOTA-skills --model <id>
    python -m agent_evals run       --sota-root ~/Github/SOTA-skills --model <id> \\
        --arms bare,library,hook,library+hook --samples 3 --out results/<date>

The API key is read from ANTHROPIC_API_KEY only. It is never logged, and the agent's own shell
cannot read it (CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import os
import sys
import time
from pathlib import Path

from .arms import ARMS, cleanup, parse_arms, sota_skill_names
from .runner import RunConfig, options_for, run_one
from .score import contamination, hidden_pass, shipped_broken, tree_changed, unverified_done
from .workspace import load_cases

HERE = Path(__file__).resolve().parent.parent


KEY_VAR = {"anthropic": "ANTHROPIC_API_KEY", "openrouter": "OPENROUTER_API_KEY"}


def _key(required: bool, provider: str = "anthropic") -> str:
    """Read the key, then REMOVE it from this process's environment: the SDK merges its env on
    top of the inherited one, so a key left here would reach the agent's shell. Claude Code's
    subprocess scrub covers the variable it is handed, not arbitrary ones like this."""
    var = KEY_VAR[provider]
    k = os.environ.pop(var, "")
    if required and not k:
        raise SystemExit("%s is not set — refusing to start (no partial runs)" % var)
    return k or "dry-run-no-key"


def openrouter_remaining(key: str) -> float | None:
    """ACCOUNT credit left (GET /api/v1/credits: total_credits - total_usage). The key's own
    usage is not the binding constraint: other keys on the same account spend the same credit.
    Measured 2026-10-02 — a $50 cap with $2.47 left on the account; 137 of 240 runs got 402."""
    import urllib.request
    req = urllib.request.Request("https://openrouter.ai/api/v1/credits",
                                 headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)["data"]
            return float(d["total_credits"]) - float(d["total_usage"])
    except Exception as e:
        print("openrouter credit check failed: %r" % (e,), file=sys.stderr)
        return None


def openrouter_usage(key: str) -> float | None:
    """Cumulative USD spent on this OpenRouter key (GET /api/v1/key -> data.usage). The SDK's
    total_cost_usd is estimated from Anthropic's price list, so it is not the budget of record
    when the calls go through OpenRouter."""
    import urllib.request
    req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                 headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return float(json.load(r)["data"]["usage"])
    except Exception as e:
        print("openrouter usage check failed: %r" % (e,), file=sys.stderr)
        return None


def cmd_dry_run(a) -> int:
    cfg = RunConfig(model=a.model or "MODEL-NOT-SET", sota_root=a.sota_root, provider=a.provider)
    for case in load_cases(a.cases, a.only):
        for arm in parse_arms(a.arms):
            ws, cd, kw = options_for(arm, case, cfg, _key(False, a.provider))
            shown = dict(kw, env={k: ("<redacted>" if ("KEY" in k or "TOKEN" in k) and v else v)
                                  for k, v in kw["env"].items()})
            skills = sorted(p.name for p in (cd / "skills").iterdir())
            print(json.dumps({"case": case.id, "arm": arm.name, "skills_installed": len(skills),
                              "hook": "hooks" in json.loads((cd / "settings.json").read_text()),
                              "options": shown}, default=str))
            cleanup(ws, cd)
    return 0


def _row(arm, case, sample, ws, tr, a, sota_skills) -> dict:
    changed = tree_changed(ws)
    hidden = hidden_pass(case.dir, ws, unsafe_local=a.unsafe_local_scoring)
    return {
        "shipped_broken": shipped_broken(tr.result, tr.error, changed, hidden.get("ok")),
        "case": case.id, "arm": arm.name, "sample": sample, "error": tr.error,
        "init_seen": bool(tr.init),
        "result": tr.result, "wall_s": tr.wall_s, "tool_calls": len(tr.tool_calls),
        "tree_changed": changed,
        "unverified_done": unverified_done(tr.tool_calls, tr.result, changed),
        "hidden": hidden,
        "contamination": contamination(arm.library, tr.init, tr.tool_calls, tr.final_text, sota_skills),
        # the hook's treatment check: it writes its ledger under .git/ when it runs at all.
        # Without this a hook that silently never registered would read as "no effect" on H1.
        "hook_ledger": (ws / ".git" / "sota-verified-done").is_dir(),
    }


def cmd_run(a, preflight: bool = False) -> int:
    key = _key(True, a.provider)
    if not a.model:
        raise SystemExit("--model is required (model ids live in config, never in code)")
    cfg = RunConfig(model=a.model, sota_root=a.sota_root, provider=a.provider,
                    max_turns=3 if preflight else a.max_turns,
                    # 0.50, not 0.05: a ONE-word reply costs ~$0.10-0.13 through Claude Code (its
                    # system prompt + tools on an uncached first turn; measured 2026-10-02), so the
                    # old cap made the preflight unpassable by construction
                    max_budget_usd=0.50 if preflight else a.max_budget_usd, timeout_s=a.timeout)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows_path = out / ("preflight.jsonl" if preflight else "runs.jsonl")
    sota_skills = sota_skill_names(a.sota_root)
    cases = load_cases(a.cases, a.only)
    if preflight:   # a prompt a working setup finishes in ONE turn: success is then observable
        from .workspace import Case
        cases = [Case(cases[0].id, cases[0].dir, "Reply with the single word OK. Do not use any tools.")]
    arms = [ARMS["bare"], ARMS["library"]] if preflight else parse_arms(a.arms)
    samples = 1 if preflight else a.samples
    jobs = [(s, case, arm) for s in range(samples) for case in cases for arm in arms]  # interleaved
    state = {"spent": 0.0, "n": 0, "stopped": False}
    base_usage = openrouter_usage(key) if a.provider == "openrouter" else None
    if a.provider == "openrouter" and base_usage is None:
        raise SystemExit("cannot read OpenRouter usage — refusing to run without the budget of record")
    if a.provider == "openrouter" and not preflight:
        left = openrouter_remaining(key)
        if left is None or left < a.total_budget_usd:
            raise SystemExit("OpenRouter account credit left: %s, below --total-budget-usd %.2f — "
                             "top up or lower the cap; a run that starves mid-way is unanalysable"
                             % ("unknown" if left is None else "$%.2f" % left, a.total_budget_usd))

    def spent_now():
        if base_usage is None:
            return state["spent"]
        u = openrouter_usage(key)
        return state["spent"] if u is None else max(state["spent"], u - base_usage)
    sem = asyncio.Semaphore(max(1, a.concurrency))
    lock = asyncio.Lock()
    (out / "traces").mkdir(exist_ok=True)

    async def one(s, case, arm, f):
        async with sem:
            if await asyncio.to_thread(spent_now) >= a.total_budget_usd:
                state["stopped"] = True
                return
            ws, cd, tr = await run_one(arm, case, s, cfg, key)
            row = await asyncio.to_thread(_row, arm, case, s, ws, tr, a, sota_skills)
            async with lock:
                (out / "traces" / ("%s__%s__%d.json" % (case.id, arm.name.replace("+", "_"), s))).write_text(
                    json.dumps(tr.__dict__, default=str, indent=1))
                f.write(json.dumps(row, default=str) + "\n"); f.flush()
                state["spent"] += (tr.result.get("total_cost_usd") or 0.0); state["n"] += 1
                print("[%3d/%d] %-6s %-13s s%d hidden=%s unverified_done=%s $%.3f %s" % (
                    state["n"], len(jobs), case.id, arm.name, s, row["hidden"].get("ok"),
                    row["unverified_done"], tr.result.get("total_cost_usd") or 0.0, tr.error or ""),
                    flush=True)
            # keep the agent's final workspace: the pre-registration allows re-scoring when the
            # scoring container failed, which is impossible once the workspace is deleted
            keep = out / "workspaces" / ("%s__%s__%d" % (case.id, arm.name.replace("+", "_"), s))
            await asyncio.to_thread(shutil.copytree, ws, keep, dirs_exist_ok=True,
                                    ignore=shutil.ignore_patterns(".git"))
            cleanup(ws, cd)

    async def all_jobs(f):
        await asyncio.gather(*(one(s, c, ar, f) for s, c, ar in jobs))

    with rows_path.open("a", encoding="utf-8") as f:
        asyncio.run(all_jobs(f))
    spent, n = spent_now(), state["n"]
    if base_usage is not None:
        print("OpenRouter spend this invocation: $%.4f (SDK estimate: $%.4f)" % (spent, state["spent"]))
    if state["stopped"]:
        print("TOTAL BUDGET %.2f reached — %d of %d jobs not run" % (a.total_budget_usd, len(jobs) - n, len(jobs)),
              file=sys.stderr)
    print("%d run(s), $%.2f, rows in %s" % (n, spent, rows_path))
    if preflight:
        return check_preflight(rows_path)
    return 0


def check_preflight(rows_path: Path) -> int:
    """The isolation controls, both directions: bare must NOT see the library, library MUST."""
    rows = [json.loads(l) for l in rows_path.read_text().splitlines() if l.strip()][-2:]
    by = {r["arm"]: r for r in rows}
    bad = []
    # A run that errored or never started a session says NOTHING about isolation: the first
    # draft printed PASS over two 401s, because an absent skill listing reads as "isolated".
    for r in rows:
        if r.get("error") or not r.get("init_seen") or (r.get("result") or {}).get("subtype") != "success":
            bad.append("%s run did not complete (%s) — isolation is unverified, not passed"
                       % (r["arm"], r.get("error") or (r.get("result") or {}).get("subtype") or "no init"))
    if by.get("bare", {}).get("contamination", {}).get("listed", 1) != 0:
        bad.append("bare arm lists sota skills — isolation is broken")
    if not by.get("library", {}).get("contamination", {}).get("treatment_present"):
        bad.append("library arm lists no sota skills — the treatment did not load")
    for b in bad:
        print("PREFLIGHT FAIL: " + b)
    print("PREFLIGHT %s" % ("FAIL" if bad else "PASS"))
    return 1 if bad else 0


PROBE_CMD = (
    "echo KEYVARS=$(env | grep -c -E '^(ANTHROPIC|OPENROUTER)_[A-Z_]*(KEY|TOKEN)=.'); "
    "curl -s -m5 -o /dev/null -w 'EGRESS=%{http_code}\\n' http://example.com || echo EGRESS=blocked; "
    "if nslookup example.com >/dev/null 2>&1 || getent hosts example.com >/dev/null 2>&1; "
    "then echo DNS=resolves; else echo DNS=blocked; fi"
)


def parse_probe(tool_calls: list) -> dict:
    """Read the probe's result from the Bash TOOL OUTPUT the harness captured — never from the
    model's reply, which can be invented. No Bash result means the probe did not run."""
    outs = [c.get("result") or "" for c in tool_calls if c.get("name") == "Bash"]
    text = "\n".join(outs)
    vals = {}
    for k in ("KEYVARS", "EGRESS", "DNS"):
        m = [l.split("=", 1)[1].strip() for l in text.splitlines() if l.strip().startswith(k + "=")]
        vals[k] = m[-1] if m else None
    return {"ran": bool(outs) and vals["KEYVARS"] is not None, **vals}


def cmd_sandbox_probe(a) -> int:
    """Run PROBE_CMD inside the agent's real sandbox (bare arm) and judge it. Fails closed if
    the API key is readable from the agent's shell or the probe did not run; records egress and
    DNS, which the pre-registration does not gate on but every report should state."""
    key = _key(True, a.provider)
    cfg = RunConfig(model=a.model, sota_root=a.sota_root, provider=a.provider, max_turns=4,
                    max_budget_usd=0.50, timeout_s=300)
    from .workspace import Case
    case0 = load_cases(a.cases, a.only)[0]
    case = Case(case0.id, case0.dir, "Run exactly this shell command once with the Bash tool and "
                "then stop. Do not modify it.\n\n" + PROBE_CMD)
    ws, cd, tr = asyncio.run(run_one(ARMS["bare"], case, 0, cfg, key))
    cleanup(ws, cd)
    res = parse_probe(tr.tool_calls)
    print(json.dumps({"probe": res, "error": tr.error, "cost": tr.result.get("total_cost_usd")}))
    bad = []
    if not res["ran"]:
        bad.append("the probe never ran in the agent's shell — the sandbox is unmeasured")
    elif res["KEYVARS"] != "0":
        bad.append("an API credential is readable from the agent's shell (KEYVARS=%s)" % res["KEYVARS"])
    for b in bad:
        print("SANDBOX PROBE FAIL: " + b)
    print("SANDBOX PROBE %s — egress %s, DNS %s" % ("FAIL" if bad else "PASS", res["EGRESS"], res["DNS"]))
    return 1 if bad else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="agent_evals", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["dry-run", "preflight", "sandbox-probe", "run"])
    p.add_argument("--sota-root", type=Path, required=True)
    p.add_argument("--cases", type=Path, default=HERE / "cases")
    p.add_argument("--only", nargs="*", help="case ids")
    p.add_argument("--arms", default="bare,library")
    p.add_argument("--model", help="provider model id, e.g. anthropic/claude-sonnet-5.5 on OpenRouter")
    p.add_argument("--provider", choices=["anthropic", "openrouter"], default="anthropic")
    p.add_argument("--samples", type=int, default=1)
    p.add_argument("--max-turns", type=int, default=40)
    p.add_argument("--max-budget-usd", type=float, default=1.00, help="per run")
    p.add_argument("--total-budget-usd", type=float, default=10.00, help="whole invocation")
    p.add_argument("--timeout", type=int, default=900, help="per run, seconds")
    p.add_argument("--concurrency", type=int, default=4, help="runs in flight at once")
    p.add_argument("--out", default="results/%s" % time.strftime("%Y-%m-%d"))
    p.add_argument("--unsafe-local-scoring", action="store_true",
                   help="run hidden tests on this host when no container runtime exists")
    a = p.parse_args(argv)
    a.sota_root = a.sota_root.expanduser().resolve()
    if a.command == "dry-run":
        return cmd_dry_run(a)
    if a.command == "sandbox-probe":
        if not a.model:
            raise SystemExit("--model is required")
        return cmd_sandbox_probe(a)
    return cmd_run(a, preflight=(a.command == "preflight"))
