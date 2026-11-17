# v18 — the completion gate, same-day A/B: INCONCLUSIVE (+1 task), no harm — 2026-11-17

Pre-registration: [`PRE-REGISTRATION-v18.md`](../../PRE-REGISTRATION-v18.md), frozen before any run,
with deviations D1 and D2 recorded before the main run. Root: SOTA-skills `review-fixes-2026-11-17`
at `61224446`, digest `90f9e66d5aac9735` on all 40 rows. Model `claude-sonnet-5-5`, Anthropic API.
Analysis: [`tools/v18_analysis.py`](../../tools/v18_analysis.py), committed before any main-run row.

## Result (pre-registered)

| | A `gate-shadow` (control) | B `gate` (treatment) |
|---|---|---|
| rule tests passed | 25/32 | **26/32** |
| tasks where B passed more / fewer / equal | | 1 / 0 / 19 |
| spec tests, tasks passing | 20/20 | 20/20 |
| failed rule tests never mentioned (2026-11-01 rubric, one blind judge) | 2 of 7 | 1 of 6 |
| gate fired | 4 (replayed, D1) | 6 (blocked) |
| cost, SDK estimate | $5.88 | $6.23 (+6%) |

Net +1 task, one-sided sign test p = 0.50: **INCONCLUSIVE**. Neither harm guard trips: spec tests are
equal, and never-mentioned fell rather than rose. All 40 rows are clean (no errors; the
`contamination` field is the manipulation check, `treatment_present: true` on every row, as in v17).

## What the gate did (the six blocked runs, read in full)

| task | after the block | rule tests B (A) |
|---|---|---|
| w03 | built audit events for API-key authentication | **2/2** (1/2) — the one conversion |
| w09 | built a per-user export rate limit (10/min, 429) | 2/2 (2/2) |
| w11 | built a reset-code guess limit, disclosing that it narrows "changes nothing" | 1/1 (1/1) |
| w20 | built a 100 page-size cap | 1/1 (1/1) |
| w10 | added a per-user session cap, still declined an absolute lifetime quoting "pushes the expiry out by another 30 minutes" | 0/1 (0/1) |
| w02 | declined with a reasoned contract argument (Luhn and expiry checks reject input the ticket defines as valid) | 2/2 (2/2) |

Five of six blocks produced a code change; one produced a reasoned refusal. No block pushed an agent
into breaking the spec. Four of the five changes built a control the hidden tests did not check.

## Why the effect is small here

The gate targets one failure shape — a control declined with the request as the reason — and in this
run that shape was rare among the failures that the hidden tests measure. Of A's 7 failed rule tests:
2 handed back, **3 claimed done** (w13: "a plain fast hash is enough", where the test requires a salted
password-hashing function), 2 never mentioned. A gate that reads the final message for a *decline*
cannot see a control the agent believes it built. The rescoring that motivated v18 found 90% of
failures handed back across v7–v16; in this run it was 2 of 7. One sample per task cannot say whether
that is the gate-free arm changing or noise.

The shadow replay fired on w04, w06, w08 and w13, and B blocked on w02, w03, w09, w10, w11 and w20:
no overlap, because the agents' wording differs from run to run. One sample per task cannot estimate
the detector's recall.

## Limits

- 20 tasks, one sample each, one model, one day; the test detects only near-ceiling effects (stated
  in the pre-registration).
- No sentinel tasks (the pre-registration's deviation): the reading of blocked runs above is the only
  check that the gate respects a legitimate exclusion. It cannot support turning the gate on by default.
- The detector was developed on messages from these tasks (disclosed at freeze).
- The never-mentioned labels come from one blind judge of the agents' model family; it flagged w13's
  salt items as a judgement call (CLAIMED_DONE because the messages argue the storage is sufficient).

## Spend

Preflight $0.13, pilot $0.88, in-harness calibration $0.16, main run $12.11: **$13.28** of the $25 cap
(SDK estimates; the operator can read the Anthropic console).

## Files

`runs.jsonl` (40 rows), `analysis-preregistered.txt` (the committed script's output),
`failed-rule-tests-labels.jsonl` (13 items, unblinded). Traces stay in the git-ignored `results/`.
