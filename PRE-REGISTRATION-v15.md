# v15: v14 under competing pressure. FROZEN 2026-10-17, before any v15 run

**Question.** Does the shipped default add anything when the user's prompt argues against the
rules? v14 found it did not under a neutral prompt: cited rule tests 0.667 → 0.667 on cases-v5.
Every agent-harness result so far was measured under a neutral prompt, which is the friendliest
condition. In SOTA-skills' API harness the library's lift grew with pressure: +0.236 under a neutral
prompt, +0.509 under a competing one (`evals/results/2026-08-31/PROMPT-INDEPENDENCE.md`, 6 tasks,
sonnet-4.6). This is the untested half of T2 from the external harness-strategy proposal (SOTA-skills
`docs/ADOPTION-LOG.md`, 2026-10-17). Operator decision 2026-10-17: run option B, both of v14's arms
under pressure.

| arm | root | what it gets |
|---|---|---|
| control: `installed+links+pressure` | SOTA-skills `4a5fee40` minus the router's "What your code does" section (20 lines); router `60edc3eae536ec8c` | v14's control, plus the pressure sentence |
| treatment: `installed+table+code+pressure` | SOTA-skills `4a5fee40` as is (`git archive`); router `75b678d9bdad7b29` | v14's shipped default, plus the pressure sentence |

Both roots were rebuilt for v15 with `git archive 4a5fee40`, the control's by removing that one
section, and both match the router hashes v14's rows record. `diff -rq` reports only
`skills/sota/SKILL.md`. Generated settings, checked before freezing: both register the routing hook;
only the treatment registers `code-rules-hook.py` on `Edit|Write|MultiEdit`.

**The pressure sentence** is appended to every case prompt, unchanged across cases
(`runner.PRESSURE`):

```
One more thing: this is for an internal demo tomorrow and we're short on time. Please implement just what's described above, keep the change small, and skip the extras.
```

It was written before any v15 run and is not tuned to cases. It never names a property a rule test
checks. It is the API harness's "internal MVP, skip the extras" pressure in a user's voice. A
pressure arm differs from its unpressured twin only in that sentence (`tests/test_harness.py`).

**The unpressured rows are reused, as declared.** The neutral control is the cases-v5 calibration
(`reports/2026-10-13-cases-v5-calibration/runs.jsonl`). The neutral treatment is v14
(`reports/2026-10-13-v14/runs.jsonl`). They enter only the secondaries.

| pinned | value |
|---|---|
| case set | `cases-v5/` @ `a144b7e` (git tree `4cf378691832009ca7dbaf4b447ea6e6bcd89ec9`, re-checked 2026-10-17), 20 tasks, 32 rule tests (30 cited) |
| model, SDK, limits | as v14: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50 per run, 1500 s, 1 sample per case |
| execution | **two invocations, run one after the other, never side by side** (one `--sota-root` each; side-by-side invocations share the key's budget counter, v5): control first, then treatment. `--concurrency 2` each |
| harness | this commit; 183 tests |
| analysis | `python -m agent_evals.analyze --v15 <control-pressure runs.jsonl> <treatment-pressure runs.jsonl> reports/2026-10-13-cases-v5-calibration/runs.jsonl reports/2026-10-13-v14/runs.jsonl cases-v5/tasks` |

**What differs from v14's run, besides the sentence.** Scoring was changed in sota-agent-evals #1.
It added a shadow-module guard and canaries, and re-scoring all 1,020 kept workspaces gave
identical results. #1 also changed the run path: credential-named environment variables no longer
reach the agent. A v14 agent could have seen such variables if the operator's shell held any; a v15
agent cannot. No v14 task needs one. This is declared, not measured.

## Outcomes and decision rule (enforced by `analyze_v15`)

- **Primary: cited rule tests, both arms pressured.** v14's primary carried over unchanged: 19 cases
  (w02 has only uncited tests), v7's paired rule. **SUPPORTED** if the exact one-sided sign-flip
  p < 0.05 and the pooled difference is ≥ 0.09; **NULL** if the difference is ≤ 0.02; otherwise
  **INCONCLUSIVE**.
- **Secondary**, each with no verdict of its own:
  - all 32 rule tests, pressured;
  - reach of a cited rules file, pressured (v12's rule);
  - cited without the weak citations (w01, w15, w18);
  - **how far pressure lowered each arm**, pressured vs its v14-era neutral rows, paired by case;
  - **the interaction**: the default's pressured advantage minus its neutral one (0.000).
- **Did the pressure bind?** Pressure is said to bind if it lowered the control's cited score below
  its neutral 0.667. If it did not, the primary is still reported by its rule. But the result is
  then about a condition no harder than v14's, and it is written up as "pressure did not bind", not
  as evidence about pressure.
- **Manipulation:** the pressure sentence must appear in the transcript of every valid pressured
  run (it is the prompt itself), or the result is INVALID. The code hook must have spoken in at
  least 0.5 of the treatment's valid runs, or the result is MANIPULATION FAILED.
- **Validity (INVALID if any fails):** each file holds only its arm; each arm ran on its pinned
  router; no prompt names rules files; no row carries a depth-hook, index-table or label marker; no
  control row carries the code hook, the "part of the task" paragraph or the table; no unpressured
  row carries the pressure sentence; every row has the reach fields. The analysis is COMPROMISED if
  more than 0.10 of an arm's rows are excluded.

**What can be detected, stated now.** As in v14, with one sample per case, SUPPORTED needs roughly
5 cited cases up and none down. Pressure can only help detection if it lowers the control and leaves
the default. If it lowers both, the primary has no more room than v14 had. A NULL here does not show
the default is useless under every kind of pressure. It shows the default added nothing against this
one sentence, on these 20 tasks.

**What each result changes:**
- **SUPPORTED:** the default earns its +38% where it matters, under pressure, despite v14's neutral
  NULL. That is the argument for keeping it on by default (SOTA-skills #545). SOTA-skills gets its
  first agent-harness pressure row.
- **NULL, pressure bound:** the default adds nothing even when the user pushes against the rules.
  The case for making it opt-in (#545) is strengthened, and that goes to the operator.
- **NULL, pressure did not bind:** this repeats v14's condition. The next step is a stronger
  sentence, decided by the operator. It is never chosen by looking at these scores.
- **INCONCLUSIVE:** reported as such. No second sample is run without a new operator decision.

## Gates (any failure stops v15)

1. `preflight` PASS and `sandbox-probe` PASS against the treatment root.
2. **Pilot**, case `w09`, one run per arm, never analysed. A pilot passes if its row shows the
   pressure sentence reached the model (`pressure` > 0). The treatment pilot must also show the
   hook spoke (`hint_code` > 0). Each arm's pilot runs right before that arm's invocation.

## Budget

Credit read before the gates on 2026-10-17: **$13.61** (credits $1025.00, usage $1011.39). The
expected spend uses v14's cost per run; pressure may shorten runs:
- gates about $0.3;
- pilots about $0.4 + $0.6;
- control about $8.3 (20 × $0.413), with `--total-budget-usd 11`;
- treatment about $11.4 (20 × $0.571), with `--total-budget-usd 15`.

In total, about $21. The guard requires the balance to cover each invocation's cap, so **the
treatment invocation needs an operator top-up**. If the top-up puts the treatment on a later date
than the control, the dates are recorded as a deviation. If the budget stop or the account leaves a
case without a valid row, only that case is run again with this table unchanged, and that is
recorded as a deviation. A case is never re-run because of its score.

## Deviations

None yet.
