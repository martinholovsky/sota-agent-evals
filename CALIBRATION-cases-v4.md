# Calibration of cases-v4 — FROZEN 2026-10-10, before any cases-v4 agent run

**What this is.** A set-level check of whether cases-v4 can discriminate. It is **not** a measurement
of any treatment, and it selects nothing: no case is dropped, edited or re-weighted on what it shows.
If the set fails, it is redesigned as a whole and calibrated again.

**Why.** v4, v5 and v6 ran on cases-v3, where hidden_pass was 1.00 in every arm. A set where every
arm scores 1.00 cannot show that reading a rule changes an outcome. cases-v4 adds RULE tests: behaviour a
named library rule requires and the prompt does not state ([build.py](cases-v4/build.py) proves
each rule test fails a solution that meets only the prompt and cites a verbatim library sentence).
Before spending on a multi-arm v7, this checks that the shipped default does not already pass them.

| pinned | value |
|---|---|
| case set | `cases-v4/` @ `b33f487` (git tree `4d12cac1adeb741494e25e691c9216375d652ec8`), 20 tasks, 53 rule tests |
| root | SOTA-skills `main` @ `3a39878`; router sha256[:16] `4e2540fca371fba7`; every citation re-verified against it |
| arm | `installed` only: what a user who ran `install.sh` gets |
| model, SDK, limits | as v6: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case, concurrency 4, one invocation |
| analysis | `python -m agent_evals.analyze --rules runs.jsonl` (descriptive) |

## Decision rule

Computed over valid rows (as v6's exclusions), in this order:

1. **UNUSABLE** if fewer than 0.60 of runs pass their spec tests (`spec_ok`). The tasks then fail
   for reasons other than the rules, and the spec is reviewed before anything else.
2. **SATURATED** if the pooled rule-test pass rate is ≥ 0.90. The shipped default already does what
   the rules require, so no treatment can show a gain. The set is redesigned.
3. **USABLE** otherwise. A v7 pre-registration follows, with arms and budget decided by the operator.

Reported alongside, with no verdict attached:
- runs passing all their rule tests;
- per case results;
- rules text in context (v6's measure) and which rules files were reached;
- mean cost and turns.

## Gates

`preflight` PASS and `sandbox-probe` PASS against the root. A pilot is unnecessary because the arm
and harness are unchanged since v6 (the only harness change is the scorer's spec/rule split; all 40
reference and naive overlays score as intended through the podman scorer).

## Budget

Account credit 2026-10-10 22:37 CEST: $19.24. `--total-budget-usd 12`; the guard requires
max($12, 4 × $3.75) = $15. v6's `installed` arm cost $0.43 per run (SDK estimate).

## Deviations

None yet.
