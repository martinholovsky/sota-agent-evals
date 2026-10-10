# Pre-registration v5 — FROZEN 2026-10-10, before any v5 run

**Why v5.** v4 showed that the routing layer gets the library *used*: 20/20 `installed` runs
invoked the `sota` router. But the chain stopped there. 1/20 invoked another skill, 3/20 went past
the router at all, and **0/20 read a rules file**, which is where every rule and Audit checklist
lives ([v4 report](reports/2026-10-09-v4/REPORT.md)). SOTA-skills ROADMAP 73 chose option (a): a
three-step "Next actions" block at the top of the router body
([PR #527](https://github.com/martinholovsky/SOTA-skills/pull/527)). v5 measures whether it moves
depth. Depth is a count of tool calls, so v4's hidden_pass ceiling does not block it.

| pinned | value |
|---|---|
| case set | `cases-v3/`, unchanged (git tree `e1933c64912f86e6aa13483c2dd6a440505a55a3`) |
| model | `anthropic/claude-sonnet-5.5` via OpenRouter, as v4 |
| Agent SDK | `claude-agent-sdk==0.2.163`; the CLI version is recorded from each run's init |
| arm | `installed` only, in both invocations (skills + the routing layer from that root's own `install.sh`) |
| control root | SOTA-skills `main` @ `b807e3f` (v1.48.0), router sha256[:16] `4e2540fca371fba7` |
| treatment root | SOTA-skills PR #527 @ `d07a30b`, router sha256[:16] `e21306b56b285b45` |
| the only difference | `skills/sota/SKILL.md` (`git diff --stat b807e3f d07a30b -- skills scripts/install.sh`: that one file) |
| per-run limits | `--max-turns 60 --max-budget-usd 1.50 --timeout 1500`, as v4 |
| samples | 1 per case: 20 runs per router, 40 in all |
| concurrency | **2 per invocation**; the two invocations start together, so both routers run through the same cases at the same time (no cross-day confound) |
| analysis | `python -m agent_evals.analyze --v5 <control runs.jsonl> <treatment runs.jsonl>` |

## Validity checks (evaluated first, in this order)

1. **Router identity.** Every row carries `router_sha`. Each file must hold exactly one and they
   must differ; the analysis enforces both (**INVALID** otherwise). That they equal the two
   pinned above is checked by hand against the `router_sha` the analysis prints, and the report
   states the result.
2. **Manipulation check.** The share of valid runs with ≥ 1 SOTA `Skill` call must be ≥ 0.5 in
   **both** arms (`MANIPULATION_MIN`). Otherwise **MANIPULATION FAILED**, never a null.
3. Every valid row has a `depth` record. Otherwise **INVALID**.

## Primary outcome and decision rule

- **Depth** = the share of valid runs with ≥ 1 `Read` of a rules file: a path matching
  `skills/sota-<name>/rules/NN-*.md`. The router's own `skills/sota/rules/` do not count; they
  hold methodology, not a domain's rules. `agent_evals/score.py:depth()` computes it from the
  tool calls. On v4's 20 valid `installed` traces it reproduces the report's hand counts
  exactly (further skill 1/20, past the router 3/20, rules read 0/20), and labelled unit tests
  cover the positive cases v4 never produced.
- **SUPPORTED** iff Fisher's exact one-sided p < **0.05** **and** treatment − control ≥ **0.20**.
- **NULL** iff treatment − control ≤ **0.05**, a negative difference included.
- **INCONCLUSIVE** otherwise.
- Power, stated now: if control stays at 0/20, treatment needs ≥ 5/20 for p < 0.05
  (0/20 vs 5/20 gives p = 0.0236).

## Descriptive, decided now (no verdict attached)

- Per arm: `rules_named` (any tool naming a rules file, e.g. Bash `cat`), `further_skill`,
  `past_router`, the skill-call rate, hidden_pass, and mean cost and turns per run. **Cost per
  run is reported because the block asks the agent to do more**, and a depth gain bought with a
  large cost rise is a different result from a free one.
- Which rules files were read, by case.

## Exclusions

- As v4: errored, contaminated and hook-mismatch rows are excluded and counted. More than 10%
  excluded in either arm is reported as **compromised**, beside the verdict.
- A run that hits the $1.50 cap is an errored row.
- **An OpenRouter in-flight `402`**: the job is re-run unchanged once, after both invocations
  finish, and the errored row is kept and counted (v4's rule). A re-run that errors again stays
  excluded.

## Budget

Account credit read 2026-10-10 before this file was frozen: **$48.18**. v4's `installed` arm
cost **$0.448 per run** (SDK estimate, n = 20, max $0.734), so 20 runs per arm is about $9.
Each invocation runs with `--total-budget-usd 13`. The pre-flight guard requires the larger
of $13 and 2 × $3.75 per invocation. Both together hold at most 4 sessions in flight, about
$15 of holds plus $26 of caps, which is below $48. Spend is reported from the account after
its counter settles, with two readings hours apart.

## Gates, immediately before the measurement

A `preflight` PASS and a `sandbox-probe` PASS against the treatment root, as in v4.

## Deviations

None yet. Any change after this file is committed is listed here with its date and reason,
before the result it could affect is read.

None before the result. Two items found **after** the run (a budget guard reading a counter both
invocations share, and a new stderr notice) are recorded in the
[report](reports/2026-10-10-v5/REPORT.md#deviations-recorded-after-the-run); neither affected a row.
