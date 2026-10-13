# v14: the shipped default on fresh tasks. FROZEN 2026-10-13, before any v14 run

**Question.** Do the two mechanisms SOTA-skills ships by default help on tasks they were not fitted
to? The mechanisms are the router's trigger table (v13) and the code-rules hook with its "part of the
task" wording (v10). Both were measured only on cases-v4, which the table's author had read. The hook
costs about +68% per agent run (its docstring, from v10), and every Claude Code user of the plugin
pays that. This is the first out-of-sample test (SOTA-skills ROADMAP 73; operator decision
2026-10-13: run the shipped-default arm, hold the table-only arm).

| arm | root | what it gets |
|---|---|---|
| control: `installed+links` | SOTA-skills `4a5fee40` minus the router's "What your code does" section; router `60edc3eae536ec8c` | library copy and routing layer; no table, no code hook |
| treatment: `installed+table+code` | SOTA-skills `4a5fee40` as is (`git archive`); router `75b678d9bdad7b29` | the same, plus the router's table section and the code-rules hook on `Edit\|Write\|MultiEdit`, as the plugin registers it |

**The control is reused, as declared.** The control rows are the cases-v5 calibration
([report](reports/2026-10-13-cases-v5-calibration/REPORT.md), `cd94538`), run earlier on 2026-10-13
with the model, SDK, limits and concurrency pinned below. The harness's run path is unchanged since
that run: this commit adds only the arm's name and root guard and the analysis. The pre-registration
for that run allowed reuse only if a later pre-registration declared it before its runs. This is that
declaration.

**What differs between the two roots:** only `skills/sota/SKILL.md`, by the 20 lines of the table
section (`diff -rq`; root-a also holds a `scripts/__pycache__` written by the offline replay below,
after its run, and read by no run). Both arms register the same routing hook. The treatment adds the
code hook. Not separable here: the table and the hook are measured together, as they ship.

| pinned | value |
|---|---|
| case set | `cases-v5/` @ `a144b7e` (git tree `4cf378691832009ca7dbaf4b447ea6e6bcd89ec9`), 20 tasks, 32 rule tests (30 cited) |
| model, SDK, limits | as the calibration and v7–v13: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50 per run, 1500 s, 1 sample per case |
| execution | one invocation of all 20 cases, `--concurrency 2` (as the control), `--total-budget-usd 18` |
| harness | this commit; 159 tests |
| analysis | `python -m agent_evals.analyze --v14 <v14 runs.jsonl> reports/2026-10-13-cases-v5-calibration/runs.jsonl cases-v5/tasks` |

## Prediction, recorded before the run (offline replay, no model calls)

The control kept every edit its agents made. Replaying the 74 code edits (Edit/Write/MultiEdit,
skipping test files) through the treatment root's `code-rules-hook.py` `select()`, the hook would
have named a cited rules file in **13 of 20** runs. The control reached one by itself in 8 of 20.
Among the **8 cases with a failed rule test**, it would have named the cited file in **7**; the
exception is w19, whose cited file (`sota-code-security` rules/19) has no row in the trigger table.
Agents under the hook may write different code, so this predicts the hook's reach, not its outcome.

## Outcomes and decision rule (enforced by `analyze_v14`)

- **Primary: cited rule tests**, which SELECTION.md binds as the primary outcome. Every rule test
  outside w02 is cited and both of w02's are uncited, so the primary is v7's paired rule over the
  19 cases other than w02. `cases_v5_uncited` derives this from `rules.json` and refuses a case
  that mixes cited and uncited tests.
- **v7's paired rule:** exact one-sided sign-flip test over per-case differences. **SUPPORTED** if
  p < 0.05 and the pooled difference is ≥ 0.09; **NULL** if the difference is ≤ 0.02; otherwise
  **INCONCLUSIVE**.
- **Secondary**, no verdict of their own: all 32 rule tests (v7's rule); reach of a cited rules file
  (v12's rule); the cited tests without the weak citations (w01, w15, w18), as a sensitivity cut.
- **Manipulation:** the hook's text (`hint_code`) reached at least 0.5 of the treatment's valid runs,
  or the verdict is MANIPULATION FAILED. The table's presence (`table_router`) is reported.
- **Validity (INVALID if any fails):** one router per arm, and the two differ; no prompt names rules
  files; no row carries a depth-hook, index-table or label marker; no control row carries the code
  hook, the "part of the task" paragraph or the table; every row has the reach fields. The analysis
  is COMPROMISED if more than 0.10 of an arm's rows are excluded.

**What can be detected, stated now.** The control failed rule tests in 8 cases, 7 of them cited.
With one sample per case, SUPPORTED needs roughly 5 cited cases up and none down. Two cases up by
two tests each, plus two up by one, gives p = 1/16, which is not enough. A real but smaller effect
reads as INCONCLUSIVE or NULL, so a NULL here does not show that the mechanisms do nothing on fresh
tasks.

**What each result changes (SOTA-skills ROADMAP 73):**
- **SUPPORTED:** the default's cost is backed out of sample. The table-only arm (about $9) is then
  worth running, for hosts that have no hooks.
- **NULL with reach up:** the files get named on fresh tasks, but the outcome does not move. The
  "part of the task" lever is suspected to be fitted to cases-v4, and the +68% default is put to
  the operator.
- **NULL with reach not up:** this contradicts the replay. The harness and the hook's delivery are
  checked before anything else.
- **INCONCLUSIVE:** reported as such. No second sample is run without a new operator decision.

## Gates (any failure stops v14)

1. `preflight` PASS and `sandbox-probe` PASS against the treatment root.
2. **Pilot**, case `w09`, never analysed. It passes if the row shows the hook spoke (`hint_code` > 0).
   The replay predicts the hook names w09's cited file (`sota-code-security` rules/01).

## Budget

Credit read before the gates on 2026-10-13: $29.97 (credits $1025, usage $995.03). About $1.4 of
the calibration had not yet settled. Expected spend: gates about $0.3; pilot about $0.7; run $12–14
(the control's $0.41 per run, × 1.68). The guard needs max($18, 2 × $3.75) = $18. If the budget stop
or the account leaves a case without a valid row, that case alone is run again with this table
unchanged and recorded as a deviation. A case is never re-run because of its score.

## Deviations

None yet.
