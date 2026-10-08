# Pre-registration v3 — FROZEN 2026-10-03, before any v3 run

v1 was compromised (credit outage) and saturated; v2 ran clean but near-saturated (hidden_pass
0.92–0.95 in every arm; 0.98–1.00 once two defective cases are set aside). v3 is harder by
construction: 20 change tasks against one multi-module application, scored on the app's full
regression suite plus task tests, with regression traps in every task, two planted bugs, and an
independent blind spec review of every hidden assertion before freezing.

| pinned | value |
|---|---|
| case set | `cases-v3/` git tree `e1933c64912f86e6aa13483c2dd6a440505a55a3` (20 cases; built by `cases-v3/build.py`, all 20 verified locally and in the scoring container) |
| model | `anthropic/claude-sonnet-5.5` via OpenRouter, every model class pinned to it |
| Agent SDK | `claude-agent-sdk==0.2.163` |
| SOTA-skills | `origin/main` at `9c00cc8` (skills/ and `scripts/verified-done-hook.py`) |
| per-run limits | `--max-turns 60 --max-budget-usd 1.50 --timeout 1500` (raised from v2's 40 / 1.00 / 900 for larger tasks, fixed now, before data) |
| concurrency | 4 |
| analysis | `python -m agent_evals.analyze --v2 runs.jsonl` (same hypotheses and code as v2) |

## Hypotheses (same as v2)

- **H1 (primary):** `shipped_broken` lower in `hook` than `bare` (H1a) and in
  `library+hook` than `library` (H1b). SUPPORTED iff the paired 95% CI lies below 0.
- **H2:** `hidden_pass` higher in `library` than `bare`. SUPPORTED iff the CI lies above 0.
- **H3:** `hidden_pass` higher in `hook` than `bare`. SUPPORTED iff the CI lies above 0.
- Descriptive only: unverified_done and the unpiped/piped/no-test breakdown.

## Budget and the cost-only sample rule

The operator approved a pilot within the current cap and will set the measurement budget B after
seeing the pilot's numbers. The pilot — t01–t03 (first three ids) × 4 arms × 1 sample — measures
mean OpenRouter cost per run C; its pass rates are not used for any decision and its rows are
excluded. Given B: **S = 3 if 240·C·1.15 ≤ B; else S = 2 if 160·C·1.15 ≤ B; else S = 1.**
A preflight PASS and a sandbox-probe PASS are required immediately before the measurement.

**Pilot result (2026-10-03, cost only — rows excluded as stated above):** 12/12 runs, 0 errors.
OpenRouter usage delta $2.7005 → **C = $0.225/run**; the SDK's own estimate summed to $2.2680
($0.189/run, ~16% low — re-derived 2026-10-04 from `results/v3-pilot/runs.jsonl`). The rule
uses the OpenRouter figure. Projected spend: S=3 $62.10, S=2 $41.40, S=1 $20.70. **Awaiting the
operator's B** (and an account top-up: credit remaining $18.53 on 2026-10-04, `GET /api/v1/credits`).

**Operator's B, set 2026-10-08 before any measurement spend: B = $20.00 → S = 1** (80·C·1.15 =
$20.70 is the S=1 projection; 160·C·1.15 = $41.40 > B). B is bounded by the account: credit was
$26.88 on 2026-10-08, and the runner checks the budget only before launching a job, so 4 jobs in
flight at the $1.50 cap can overshoot by up to $6. B + $6 stays under the credit, so the v1
failure mode (a mid-run credit outage) cannot recur. Expected spend 80 × $0.225 = $18.00. If
per-run cost runs more than ~11% above the pilot, the run stops at B, and the shortfall is
reported as an incomplete run rather than as data. S=1 means one run per case × arm: 20 paired
cases per comparison.

## Exclusions and validity (decided now)

- Errored, contaminated and hook-mismatch rows are excluded and counted; more than 10% excluded
  in any arm → reported as compromised.
- No-result scoring (`hidden.ok` None) excluded from that metric and counted.
- **Ceiling rule:** if mean hidden_pass ≥ 0.95 in both arms of a comparison, that comparison is
  reported as uninformative whatever its verdict line says.
- **Defective-case rule (learned in v2):** a case failing identically in every run of every arm
  is inspected against its spec after the run; if its hidden test contradicts the written spec,
  the pre-registered result over all 20 still stands and a sensitivity analysis without it is
  reported, labelled post-hoc. Cases are never edited after freezing.

## Deviations

None yet.
