# v5 measurement — 2026-10-10

**The router's "Next actions" block did not get agents to the rules files.**

- **Primary, by the frozen rule: NULL.** Runs that read ≥ 1 rules file: control **0/20**,
  treatment **1/20**. The difference is +0.05, on the null band's edge, with Fisher one-sided
  p = 0.50.
- **Validity: passed.** Each file holds one router hash, the two differ, and both match the
  pinned values by hand (`4e2540fca371fba7`, `e21306b56b285b45`). The manipulation check gave
  20/20 in both arms. 0 rows were excluded.
- **Descriptive (no verdict attached):** the block moved its *first* step a little. A further
  skill was invoked in 0/20 control runs and 3/20 treatment runs, and "past the router" went
  from 0/20 to 4/20. All three runs that invoked a language or domain skill stopped at its
  `SKILL.md` and opened no rules file.

Pre-registration: [PRE-REGISTRATION-v5.md](../../PRE-REGISTRATION-v5.md), frozen and pushed at
`f5513ce` before any v5 run.

## Configuration

| | |
|---|---|
| model | `anthropic/claude-sonnet-5.5` via OpenRouter |
| arm | `installed` in both invocations, started together, concurrency 2 each |
| control | SOTA-skills `main` @ `b807e3f` (v1.48.0) |
| treatment | SOTA-skills PR #527 @ `d07a30b`: the router with the "Next actions" block; nothing else differs under `skills/` or in `install.sh` |
| per-run limits | 60 turns, $1.50, 1500 s |
| gates, immediately before | preflight PASS ($0.23); sandbox-probe PASS (key vars 0, egress 403, DNS blocked) |
| harness | `claude-agent-sdk==0.2.163`, bundled CLI `2.1.286` (from each run's init, as v4), 99/99 tests |
| analysis | `python -m agent_evals.analyze --v5 runs-control.jsonl runs-treatment.jsonl` → `analysis-preregistered.json` |

## Results

| | control | treatment |
|---|---|---|
| runs (excluded) | 20 (0) | 20 (0) |
| invoked a SOTA skill (manipulation check) | 20/20 | 20/20 |
| **read ≥ 1 rules file (primary)** | **0/20** | **1/20** |
| named a rules file in any tool | 0/20 | 1/20 |
| invoked a further sota skill | 0/20 | 3/20 |
| went past the router in any way | 0/20 | 4/20 |
| hidden_pass | 1.00 | 1.00 |
| mean cost per run (SDK estimate) | $0.396 | $0.411 (+4%) |
| mean turns | 21.25 | 21.35 |

**Where the treatment went past the router:**

- **t07** invoked only the router and then read two rules files that fit the task:
  `sota-api-design/rules/06-webhooks.md` and `sota-code-security/rules/22-constant-time-comparison.md`.
  This is the only run of the 40 that reached a rule.
- **t06** invoked `sota-python`; **t13** invoked `sota-python` and `sota-testing`; **t15** invoked
  `sota-python` and `sota-api-design`. None of them read a rules file.

## What this says

The block changed the step that names a skill, not the step that opens a rules file. When an
agent did invoke a language skill, it treated loading that skill's `SKILL.md` as the end of
the chain, which is the same stopping pattern the router showed in v4, one level down. An
instruction at the top of the router does not carry through to the next file's index. Of the
options recorded in SOTA-skills ROADMAP 73, this argues against more router text and toward
**(c)**: a mechanical hook on the `Skill` tool that, after a skill loads, names the rules file
to open for the files being edited.

hidden_pass stayed at the ceiling, so v5 says nothing about whether reading the rules would
change outcomes. This report does not claim it would.

## Deviations, recorded after the run

1. **The per-invocation budget guard read a shared counter.** Both invocations used one
   OpenRouter key, and the guard takes the larger of the SDK estimate and the key's usage
   delta. So each invocation's guard saw **both** invocations' spend. Treatment's guard figure
   ended at $13.39 against its $13.00 cap, so it could have stopped that arm before 20 runs.
   It did not: all 40 jobs ran and no row is affected. This is a harness defect for any
   side-by-side run and is open in the README.
2. The CLI now prints "Permission mode forced to default — CLAUDE_CODE_SUBPROCESS_ENV_SCRUB is
   set" to stderr. Every run's init reports the same CLI version (2.1.286) and permission mode
   (`default`) as v4, so this is a new message, not a new configuration.

## Spend

| reading | account usage | note |
|---|---|---|
| before the gates (2026-10-10) | $851.8180 | |
| 2026-10-10 12:10 CEST | $865.3783 | +$13.56; the counter lags (v3, v4) |
| 2026-10-10 21:13 CEST | $865.4539 | +$0.08 over nine hours: settled. **v5 cost $13.64** |

The SDK estimate was $16.13 for the 40 runs plus $0.27 for the gates; the account, the budget of
record, settled lower at $13.64.

## Limits

- n = 20 per router, one sample per case, one model. With control at 0/20, the design detects a
  rise to ≥ 5/20; a true effect smaller than that reads as NULL here.
- Depth is counted from tool calls. A rules file seen by other means is not counted, so depth can
  only be under-stated.
- v4 measured 3/20 past the router on an earlier router (`1d19530`); this control measured 0/20 on
  `b807e3f`. That comparison crosses days and router versions and is not interpreted.
