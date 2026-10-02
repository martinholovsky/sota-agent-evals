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

## Deviations

None yet.
