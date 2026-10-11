# Pre-registration v8 — FROZEN 2026-10-11, before any v8 run

**Why v8.** v7 ([report](reports/2026-10-11-v7/REPORT.md)) showed two things:
- Reading the cited rules files raised rule tests from **0.698 to 0.868** (SUPPORTED).
- v6's depth hook got agents to a cited file in **12/20** runs, yet moved rule tests only **+0.019**
  (NULL). Those runs saw about **79** rules lines per run, against about **448** when the files
  were named.

SOTA-skills ROADMAP 73 option (d') therefore changes the hook's instruction from a judgement ("Read
the ones whose topic matches") to one concrete action: choose one or two files, then **read each in
full**. The operator chose this design on 2026-10-11, over a prompt-matching selector. That
selector was measured offline before this file: a BM25 match of the prompt against the rules index
found a cited file for only 6/20 cases, because the prompts omit the rule's vocabulary by
construction.

**The treatment.** SOTA-skills branch `roadmap-73-d-full-read` @ `8c48945`, `scripts/skill-depth-hook.py`,
registered as in v6/v7 (PostToolUse on `Skill`). The only change from v7's hook is the text after a
`sota-*` skill loads. It now says: "choose the one or two files whose topic matches this task …
and Read each of them in full — every line, with no offset, limit, head, line range or grep … check
your diff against the Audit checklist at the end of each file you read". The text after the router
loads is unchanged.

| pinned | value |
|---|---|
| case set | `cases-v4`, as v7 (git tree `33e4aa795f9a2e49d6893893f98c8193fe861e37`) |
| model, SDK, limits | as v7: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case, concurrency 4 |
| root | SOTA-skills `8c48945`. Its `skills/` and `scripts/install.sh` are identical to v7's root (`git diff --stat 6e96ea8 8c48945 -- skills scripts/install.sh` is empty, and `6e96ea8`'s `skills/` equals `330bc4a`'s); router sha256[:16] `4e2540fca371fba7` |
| treatment arm | `installed+depth` against this root: 20 runs, one invocation |
| control | **v7's 20 `installed` rows** (`reports/2026-10-11-v7/runs.jsonl`), reused, not re-run |
| harness | sota-agent-evals `b96d263`, 138 tests |
| analysis | `python -m agent_evals.analyze --v8 runs.jsonl reports/2026-10-11-v7/runs.jsonl` |

**Why the control is reused, and the risk that carries.** The operator asked to keep paid runs
few. The `installed` arm passed 37/53 rule tests in the calibration (2026-10-10) and again in v7
(2026-10-11), on the same root `skills/`, model and cases, with two cases trading one test each.
A control from another time is still weaker than a concurrent one: drift on the provider's side
would be read as an effect. The report states this beside the verdict.

## Gates (any failure stops v8)

1. `preflight` PASS and `sandbox-probe` PASS against the root.
2. **Pilot** on `w20`, the treatment arm, never analysed. It passes if the row has a transcript
   and the hook's text reached the model, and if that text contains "Read each of them in full".
   The last check shows the new hook ran, not v7's.

## Validity, manipulation, decision rule

All enforced by `analyze_v8`, and identical to v7's except where stated.
- **INVALID** if any of these holds:
  - more than one router across the two files;
  - an arm other than `installed+depth` in the v8 file;
  - any row whose prompt named rules files;
  - any control row that received the hook's text;
  - a valid row with no transcript;
  - an arm with no valid rows.
- **MANIPULATION FAILED** if the hook's text reached fewer than 0.5 of the treatment's valid runs.
- **Primary** = pooled rule tests over cases scored in both, paired by case. Exact one-sided
  sign-flip test.
  - **SUPPORTED** iff p < 0.05 and the difference ≥ 0.09.
  - **NULL** iff the difference ≤ 0.02.
  - **INCONCLUSIVE** otherwise.

## Descriptive, decided now (no verdict attached)

- **Mechanism check: mean rules lines seen per run.** v7 measured about 79 with the old hook and
  about 448 with the files named. If v8 stays near 79, the instruction to read in full was not
  followed. The report will then say "not followed", not "full reads do not help".
- Runs that opened a cited rules file, from the tool inputs in the transcript (v7's 12/20).
- Per case: rule tests, control → treatment, beside v7's old-hook and named arms.
- Mean cost and turns per run.

## Exclusions and budget

- Exclusions as v7.
- Expected cost: 20 runs at about $0.43–0.50 each (SDK), about $9–10, plus gates and pilot about
  $1.20. `--total-budget-usd 15`; the guard requires $15. Credit before the run is read and reported.

## Deviations

None yet.
