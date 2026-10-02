# Pre-registration — DRAFT (freeze before the first measurement run)

Status: **draft**. Freeze by committing with a date and the case-set hash, *before* any
measurement run. A pre-registration edited after seeing results is not one.

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

- Case set: ≥20 cases, written before any run, selection rule in the `cases.jsonl` header,
  never edited by observed performance. Each case passes the solvable/not-presolved test.
- Arms: all four, interleaved per case and sample.
- Samples: 3 per case × arm (n = 60 per arm at 20 cases).
- Model, SDK version and SOTA-skills commit: recorded in the run output; fixed for the run.
- Budgets: `--max-turns 40`, `--max-budget-usd 1.00`, `--timeout 900`.

## Exclusions (decided now, not after)

- Rows with `error` (timeout, SDK failure) are reported and excluded from rates.
- Rows where `unverified_done` is `None` (did not end normally) are excluded from H1 only.
- Contaminated rows (bare/hook arm touched the library; library arm without treatment) are
  excluded and counted; if more than 10% of an arm is contaminated, the run is void.

## Analysis

Per-arm rates with 95% bootstrap CIs over cases (cases, not runs, are the unit of resampling);
paired differences per case. Report every arm, including nulls. A measure where both arms sit at
the ceiling is a fact about the instrument, never about the treatment (rules/01 §8.1).
