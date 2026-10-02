# Pre-registration v2 — FROZEN 2026-10-02, before any v2 run

The v1 run (reports/2026-10-02) was compromised by a credit outage and saturated
(hidden_pass 0.95–1.00 in every arm). v1's pre-registration is closed; this is a new one.

| pinned | value |
|---|---|
| case set | `cases-v2/` git tree `e1d8e810c42a17ad6a3751eef9dab3e6f812b4dc` (20 cases) |
| model | `anthropic/claude-sonnet-5.5` via OpenRouter (every model class pinned to it) |
| Agent SDK | `claude-agent-sdk==0.2.163` |
| SOTA-skills | `origin/main` at `39e6560` |
| budgets | `--max-turns 40 --max-budget-usd 1.00 --timeout 900 --concurrency 4`; total cap for pilot + measurement **$36.02** (operator's $50 minus $13.98 already spent) |
| analysis | `python -m agent_evals.analyze --v2 runs.jsonl` (`HYPOTHESES_V2`), committed with this file |

## Hypotheses

- **H1 (primary): the hook reduces broken "done".** `shipped_broken` (ended normally, tree
  changed, hidden tests FAIL) is lower in `hook` than `bare` (H1a) and in `library+hook`
  than `library` (H1b). SUPPORTED iff the 95% CI of the paired difference lies below 0.
  This replaces v1's `unverified_done`, which the hook satisfies by construction.
- **H2: the library raises hidden_pass** (library vs bare). SUPPORTED iff the CI lies above 0.
- **H3: the hook raises hidden_pass** (hook vs bare). SUPPORTED iff the CI lies above 0.
- Reported descriptively, not tested: unverified_done and the piped/unpiped/no-test breakdown.

## Design

- 20 cases × 4 arms × S samples, interleaved; cases are the resampling unit (10,000 bootstrap
  iterations, seed 0); per-case means over samples; paired differences.
- **S, by a cost-only rule:** a pilot of d01–d03 × 4 arms × 1 sample measures mean cost C per
  run. Remaining = $36.02 − pilot spend. S = 3 if 240·C·1.15 ≤ remaining; else S = 2 if
  160·C·1.15 ≤ remaining; else S = 1. Pilot pass rates are not inspected for this; pilot rows
  are excluded from the analysis.
- Preflight PASS immediately before the measurement; the runner refuses to start unless the
  OpenRouter account credit covers the cap.

## Exclusions (decided now)

- Errored rows (any `error`), contaminated rows, and hook-treatment mismatches are excluded
  and counted. If more than 10% of any arm is excluded, the run is reported as compromised.
- `shipped_broken` / `hidden_pass` of `None` (no result) are excluded from that metric only.
- A measure at the ceiling or floor in both arms of a comparison is reported as uninformative
  for that comparison, whatever the verdict line says (rules/01 §8.1).

## Rule applied — before the measurement run

Pilot (`results/v2-pilot`, 12 runs, excluded): 12/12 completed, 0 errors, every treatment and
hook-ledger check correct. C = **$0.108/run** (max $0.164). Pilot + its preflight ≈ $1.40, so
remaining ≈ $34.60. 240·C·1.15 = **$29.81** fits → **S = 3**. Measurement cap: **$34.50**.
Pilot pass rates were not inspected.

## Deviations

- **After the run: d08 and d15 are defective** — their hidden tests encode my reference's
  reading where the written spec says otherwise (d08: "each on its own line"; d15: the backslash
  is "dropped", so the preceding space survives). Found by inspecting the only failing cases.
  The pre-registered analysis over all 20 cases stands as reported; a sensitivity analysis
  without them is reported separately and labelled **post-hoc**
  (`reports/2026-10-02-v2/REPORT.md`). The case files are NOT edited.
