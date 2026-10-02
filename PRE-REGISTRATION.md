# Pre-registration — FROZEN 2026-10-02, before any measurement run

Status: **frozen**. Written and committed before the first live run of the measurement set.
Any change after results are seen goes in a dated *Deviations* section below, never in place.

| pinned | value |
|---|---|
| case set | `cases/` git tree `4a6ed7543b21d41aae4551a29a01e0da232d5dc7` (20 cases, commit `d14c937`) |
| model | `claude-sonnet-5-5` (operator choice) |
| Agent SDK | `claude-agent-sdk==0.2.163` |
| SOTA-skills | `origin/main` at `5a2e1fb` (skills/ and `scripts/verified-done-hook.py`) |
| budgets | `--max-turns 40 --max-budget-usd 1.00 --timeout 900`, `--total-budget-usd 100`, `--concurrency 4` |

## Hypotheses

- **H1 (hook).** `unverified_done` is lower in `hook` than in `bare`, and in `library+hook` than
  in `library`. Falsified if the difference is ≤ 0 or its 95% CI includes 0.
- **H2 (library, agent loop).** `hidden_pass` is higher in `library` than in `bare`. This
  re-measures, inside a real agent session, a lift SOTA-skills has so far measured only as one
  chat-completion call. Falsified as for H1.
- **H3 (hook does not trade correctness for compliance).** `hidden_pass` in `hook` is not lower
  than in `bare` (a hook that makes agents run *some* command without improving outcomes is a
  checkbox).

## Design

- Case set: the 20 cases pinned above, selection rule in the `cases.jsonl` header, never
  edited by observed performance. All 20 pass the solvable/not-presolved test locally and
  their reference solutions pass the hidden tests in the podman scoring container (20/20).
- Arms: all four, interleaved per case and sample.
- Samples: 3 per case × arm (n = 60 per arm at 20 cases).
- Model, SDK version and SOTA-skills commit: as pinned above, fixed for the run.
- A preflight must PASS (both runs complete, bare lists no sota skill, library lists them)
  immediately before the run; a failed preflight means no measurement.
- If the total budget stops the run early, the jobs not run are reported, and analysis uses
  only cases complete in all four arms (paired).

## Exclusions (decided now, not after)

- Rows with `error` (timeout, SDK failure) are reported and excluded from rates.
- Rows where `unverified_done` is `None` (did not end normally) are excluded from H1 only.
- Contaminated rows (bare/hook arm touched the library; library arm without treatment) are
  excluded and counted; if more than 10% of an arm is contaminated, the run is void.

## Analysis

Per-arm rates with 95% bootstrap CIs over cases (cases, not runs, are the unit of resampling);
paired differences per case. Report every arm, including nulls. A measure where both arms sit at
the ceiling is a fact about the instrument, never about the treatment (rules/01 §8.1).

## Addendum — 2026-10-02, still before any measurement run

- The analysis is `agent_evals/analyze.py`, committed with this addendum and tested on
  synthetic rows with a known effect and a known null. Verdicts: H1 SUPPORTED iff the 95% CI of
  the paired difference lies entirely below 0; H2 iff entirely above 0; H3 (non-inferiority)
  iff the CI's lower bound is above **−0.10** (a hook may cost at most 10 points of hidden-test
  pass rate). The −0.10 margin is fixed here, before data, not chosen afterwards.
- A run whose scoring container could not start (`hidden.ok` is `None`, runtime rc 125–127)
  has no hidden-test result: it is excluded from hidden_pass and counted, never scored as a
  failure. If more than 5% of rows lack a result, the scoring is re-run on the kept
  workspaces before analysis.

## Addendum 2 — 2026-10-02, still before any measurement run (operator decisions)

Supersedes the pinned *model* and *budgets* rows above; the reasons are recorded here, not
edited into the table.

- **Provider: OpenRouter** (the Anthropic key was rejected by the API itself, HTTP 401). Calls
  go through OpenRouter's Anthropic-compatible endpoint per its Claude Code guide; every model
  class is pinned to the measured model. OpenRouter's guide says to stay on Anthropic models
  for tool-use reliability, so only Anthropic models are candidates.
- **Budget of record: OpenRouter's own spend** (`GET /api/v1/key` → `usage`, delta over the
  invocation), not the SDK's estimate. **Total cap $50** for preflight + pilot + measurement.
- **Model, by a cost-only rule fixed now:** a pilot of 12 runs — cases c01–c03 (the first three
  ids, chosen by id, not by outcome) × 4 arms × 1 sample — on `anthropic/claude-sonnet-5.5`
  measures mean OpenRouter cost per run, C. If 240 × C × 1.15 fits in the remaining budget, the
  measurement uses Sonnet 5.5 with 3 samples. Otherwise `anthropic/claude-haiku-4.5`
  (half the per-token price; assumed C/2) with 3 samples; and if that does not fit, 2 samples.
  **Pilot pass rates are not looked at for this decision and pilot rows are excluded from the
  analysis.**

## Rule applied — 2026-10-02, before the measurement run

Pilot (`results/2026-10-02-pilot`, 12 runs, excluded from the analysis): 12/12 completed, no
errors; every treatment check correct (library arms list 42 sota skills, bare/hook arms
uncontaminated, the hook's ledger present in exactly the hook arms). Mean OpenRouter cost
C = **$0.105/run** (max $0.175; OpenRouter delta equalled the SDK estimate to the cent).
240 × C × 1.15 = **$28.98** ≤ remaining $48.44 → **`anthropic/claude-sonnet-5.5`, 3 samples**.
Pilot pass rates were not inspected for this decision. Measurement invocation cap: $45.

## Deviations

None yet.
