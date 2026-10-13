# Calibration of cases-v5: FROZEN 2026-10-13, before any cases-v5 agent run

**What this is.** A set-level check of whether cases-v5 ([SELECTION.md](cases-v5/SELECTION.md))
leaves room for a mechanism to show a gain. It measures no treatment and selects nothing: no case is
dropped, edited or re-weighted on what it shows. It uses cases-v4's decision rule, as SELECTION.md
binds it to.

**Which arm, and why.** The comparisons this set exists for (SOTA-skills ROADMAP 73) ask whether
the two mechanisms shipped on cases-v4 evidence still help out of sample: the router's trigger table
(v13, shipped in v1.49.0) and the code-rules hook (v10). Their common control is the library
**without either**. If that control already passes the rule tests, neither mechanism can show a
gain here, so that is the arm to calibrate. (cases-v4 calibrated the then-shipped default for the
same reason: it was the control of every later arm.)

| pinned | value |
|---|---|
| case set | `cases-v5/` @ `a144b7e` (git tree `4cf378691832009ca7dbaf4b447ea6e6bcd89ec9`), 20 tasks, 32 rule tests (30 cited, 2 uncited) |
| root | SOTA-skills `4a5fee40` (v1.49.1, the citation commit) exported with `git archive`, with **one** edit: the router's section "What your code does: the rules file to read" removed, 20 lines (the trigger table and the "part of the task" paragraph that entered the router with it in #536). Router sha256[:16] `60edc3eae536ec8c`. Diffed against `4a5fee40`: 20 lines out, 0 in, file list identical. |
| arm | `installed+links`: identical install to `installed` (library copy plus the routing layer read from the root's `install.sh`; the only hook is `UserPromptSubmit`, checked with `settings_for`). The name is forced by the root: its router keeps v12's relative links, and `cli` refuses `installed` on a links root. |
| model, SDK, limits | as v7–v13: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50 per run, 1500 s, 1 sample per case |
| execution | one invocation of all 20 cases, `--concurrency 2`, `--total-budget-usd 10` |
| harness | `agent_evals/` last changed in `8574ac3` (v13); 155 tests pass |
| analysis | `python -m agent_evals.analyze --rules runs.jsonl` (descriptive) |

## Decision rule (cases-v4's, unchanged)

Over valid rows (as v6's exclusions), in this order:

1. **UNUSABLE** if fewer than 0.60 of runs pass their spec tests. The spec is reviewed first.
2. **SATURATED** if the pooled rule-test pass rate (all 32) is ≥ 0.90. No comparison arm is bought
   on this set; ROADMAP 73 records that cases-v5 cannot separate the mechanisms.
3. **USABLE** otherwise. A comparison pre-registration follows, with arms and budget decided by the
   operator.

A verdict needs a valid row for **all 20 cases**. A case without one (budget stop, a 402 from the
account, a scorer failure) is run again, alone, after the cause is fixed, with this table unchanged,
and recorded as a deviation. A case is never re-run because of its score.

Reported alongside, with no verdict attached:
- the pooled pass rate on the 30 **cited** rule tests (SELECTION.md's primary outcome), and that rate
  without the weak citations (w01, w15, w18). The scorer records counts, not names, so per-test
  results come from re-scoring the kept workspaces through the same podman scorer (no model calls);
- runs passing all their rule tests, and per case results;
- which cited rules files were reached (`cited_reach`), rules text in context, mean cost and turns.

**Reuse.** If a later comparison wants these rows as its control, its own pre-registration must say
so before its runs, and the model, SDK, harness and this root must be unchanged. Otherwise the
control is run again.

## Gates

1. All 40 reference and naive overlays score as intended through the harness's podman scorer
   (`hidden_pass`): every reference passes spec and all rule tests, every naive passes spec and no
   rule test. **Done before this freeze: 40 of 40, rule totals summing to 32.**
2. `preflight` PASS and `sandbox-probe` PASS against the root.

No pilot: the arm's install is unchanged since v12 and the case loader since v13. The dry run loads
all 20 cases against this root and arm.

## Budget

Account credit 2026-10-13, read before the gates: **$12.07**. Expected cost is $7–9 (per-run means of
the installed arms on cases-v4: $0.37–0.45). The guard needs max($10, 2 × $3.75) = $10. Concurrency is
2 rather than 4 because 4 × $3.75 = $15 is above the credit. The budget stop can leave cases unrun if
runs cost more than $0.50 on average; those are handled as stated above, not by a higher cap.

## Deviations

None yet.
