# v18: the completion gate (SOTA-skills ROADMAP 96), same-day A/B. FROZEN 2026-11-17, before any v18 run

Status: **FROZEN 2026-11-17**, before any v18 run or API spend. Spend approved by the operator
2026-11-17 ("spend allowed"); no figure was given, so the cap is **$25**, the cap the operator set
for v14–v17, and this run stops before it.

## Question

The reasons rescoring ([report](reports/2026-11-17-handback-reasons/REPORT.md)) found that 48% of
the library's hand-backs give the request as the reason for not building a control. SOTA-skills'
opt-in `scripts/completion-gate-hook.py` blocks the stop once when a final message does that.
**Does blocking once turn those hand-backs into built controls, without lowering the spec pass
rate or teaching agents to stop reporting omissions?**

## Arms (same day, same model, same root, same cases, one invocation, interleaved)

| arm | `--arms` | what differs |
|---|---|---|
| A control | `installed+table+code+gate-shadow` | gate on Stop in `shadow` mode: detects and records, never blocks |
| B treatment | `installed+table+code+gate` | gate `on`: blocks once per turn, at most 3 per session |

Both arms load the same SOTA-skills root: `review-fixes-2026-11-17` at ``61224446``, root digest
``90f9e66d5aac9735`` (`--expect-root-digest`). The only configuration difference is the gate's mode, held
by `tests/test_harness.py::test_gate_arms_register_the_stop_hook_in_their_mode_and_fail_closed`.
Both run the same detector, so the difference is the block, not the detection.

## Cases

`cases-v5`, all 20 tasks, one sample per task per arm (40 runs). **Disclosed contamination:** the
gate's detector patterns were developed on agents' final messages from v14–v16 runs on these same
tasks (never on their hidden tests). That can raise the gate's firing rate here relative to new
tasks; it cannot change what a hidden test accepts.

**Deviation from the draft** ([PREREG-DRAFT](reports/2026-11-17-handback-reasons/PREREG-DRAFT.md)):
the four sentinel tasks (where not building is correct) are not written for this run; the budget
does not cover authoring and running them. In their place, every run where the gate blocked is read
in full afterwards and classified: did the block push against an explicit prohibition, a genuine
design decision, a declared prototype, or a control already enforced elsewhere? **This run cannot
support turning the gate on by default**; sentinels remain required before that.

## Model, provider, limits

- `--provider anthropic`, `--model claude-sonnet-5-5`, as v17. Key from SOTA-skills' git-ignored
  `.env`, exporting only `ANTHROPIC_API_KEY`, never echoed.
- `--max-turns 60`; `--max-budget-usd 1.50` per run; `--concurrency 2`; `--samples 1`.

## Outcomes and decision rule

- **Primary:** rule tests passed per arm, over all rule tests of the 20 tasks; and task-level
  paired counts (tasks where B passes more rule tests than A, and fewer).
  **SUPPORTED** if B − A ≥ +3 tasks net **and** one-sided paired sign test p < 0.05 over discordant
  tasks; **NULL** if B − A ≤ 0 tasks net; otherwise **INCONCLUSIVE**.
- **Harm guards (override SUPPORTED):** B's spec-test pass count lower than A's by more than 1 task
  → **HARM**. B's never-mentioned count among failed rule tests (scored with the 2026-11-01 rubric)
  higher than A's by more than 1 → **HARM (reporting)**.
- **Secondary (descriptive):** gate fired per arm (A from shadow records); funnel in B — fired →
  relevant edit after the block → rule test passed; the detector's recall and precision in A
  against which runs failed a rule test with a request-given reason; cost per run; turns; the
  blocked-run reading above.

## What can be detected, stated now

With 20 tasks and one sample, a one-sided sign test needs at least 5 discordant tasks all in B's
favour (p = 0.031); 4 of 4 gives 0.0625. A real but small effect reads INCONCLUSIVE.

## Prediction (recorded before any run)

The gate fires in A on about 5–8 of 20 runs (detector recall about half to three quarters of
request-reason hand-backs). In B, perhaps half of those blocks convert to a passing rule test:
B − A of +1 to +4 tasks, **most likely INCONCLUSIVE**. Spec tests unchanged. Cost in B up by under
15% (one extra turn on blocked runs only).

## Gates (any failure stops v18)

`preflight` on the root for both arms (the arm resolves, the router, code hook and gate reach the
config, the row carries the root digest); then a one-run pilot per arm, which must show a gate
record in the run's git dir for A. Both must pass before the 40 runs.

## Budget (cap $25, gates + pilot + run)

v17 cost $8.30 for 24 runs on this provider (about $0.35 a run). Expected: gates and pilot about
$1.5; run about $14–16 (40 runs, plus one continuation on blocked B runs). Worst case, from what
the runner enforces:
- **gates and pilot: a hard stop at $2.50** together; above that v18 stops and returns to the
  operator;
- **run:** one invocation, `--total-budget-usd 19`; the guard checks the summed SDK estimate
  before each run, with at most 2 × $1.50 in flight when it trips: at most $22.

Worst case total $24.50. The spend of record is the SDK estimate; the operator can read the
Anthropic console.

## Deviations

(None yet.)

## Harness change made before freezing

`ROOT_DIGEST_FILES` now includes `scripts/completion-gate-hook.py`, so the pinned digest covers the gate
itself; roots without the file hash as before.
