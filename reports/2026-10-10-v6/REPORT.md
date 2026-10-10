# v6 measurement — 2026-10-10

**The `Skill` hook got agents to the language skill almost every time, and to the rules files
about as rarely as before.**

- **Primary, by the frozen rule: INCONCLUSIVE.** Runs whose tool results carried rules-file
  text: control **2/20**, treatment **4/20**. The difference is +0.10, with Fisher one-sided
  p = 0.33. That is above the null band (≤ 0.05) and below the support bar (≥ 0.20 and p < 0.05).
- **Validity: passed.**
  - One router across the file (`4e2540fca371fba7`, as pinned).
  - A CLI transcript for 40/40 rows.
  - The hook's text reached 0/20 control runs and 20/20 treatment runs.
  - A SOTA skill was invoked in 20/20 runs in each arm.
  - No rows were excluded, every run ended `success`, none hit the $1.50 cap, and there were no errors.
- **Descriptive (no verdict attached):** the hook moved the step it names as a single action.
  - A further skill was invoked in **0/20 → 18/20** runs. In 18 of 18 that skill was `sota-python`, the one the hook named.
  - The next step asks for a choice: "Read the ones whose topic matches". It was taken in 4 of those 18.

Pre-registration: [PRE-REGISTRATION-v6.md](../../PRE-REGISTRATION-v6.md), frozen and pushed at
`88c61e1` before any v6 run (harness `8680c76`).

## Configuration

| | |
|---|---|
| model | `anthropic/claude-sonnet-5.5` via OpenRouter |
| root | SOTA-skills PR #528 @ `31b0359`; `skills/` and `install.sh` identical to `main` @ `b807e3f` |
| arms | `installed` vs `installed+depth` (the same, plus `scripts/skill-depth-hook.py` as a PostToolUse hook on `Skill`) |
| execution | one invocation, jobs interleaved case by case, concurrency 4, 21:28–21:47 CEST |
| per-run limits | 60 turns, $1.50, 1500 s |
| gates, immediately before | preflight PASS ($0.23); sandbox-probe PASS (key vars 0, egress 403, DNS blocked); pilot PASS on `t01` (transcripts in both rows, hook text in treatment only; not analysed) |
| harness | `claude-agent-sdk==0.2.163`, bundled CLI `2.1.286`, permission mode `default` (from each run's init, as v4 and v5); 117/117 tests |
| analysis | `python -m agent_evals.analyze --v6 runs.jsonl` → `analysis-preregistered.json` |

## Results

| | control (`installed`) | treatment (`+depth`) |
|---|---|---|
| runs (excluded) | 20 (0) | 20 (0) |
| invoked a SOTA skill (manipulation) | 20/20 | 20/20 |
| hook text reached the model (manipulation) | 0/20 | 20/20 |
| **rules text in a tool result (primary)** | **2/20** | **4/20** |
| a `Read` of a rules file (v5's primary) | 1/20 | 2/20 |
| any tool input naming a rules file | 1/20 | 4/20 |
| invoked a further sota skill | 0/20 | 18/20 |
| went past the router in any way | 1/20 | 18/20 |
| mean rules lines seen per run | 21.2 | 8.2 |
| hidden_pass | 1.00 | 1.00 |
| mean cost per run (SDK estimate) | $0.428 | $0.448 (+5%) |
| mean turns | 21.75 | 25.2 (+16%) |

**Where rules text reached the model.** I checked each of the six positive rows by hand in its
transcript:

- control **t07**: Bash read `sota-api-design/rules/06-webhooks.md` and
  `sota-privacy-compliance/rules/03-consent-and-user-rights.md` (104 lines).
- control **t10**: `Read` of `sota-shell-scripting/rules/06-ad-hoc-commands.md` (320 lines).
- treatment **t05**: `Read` of `sota-python/rules/05-security.md` and
  `sota-code-security/rules/01-input-injection.md`.
- treatment **t07**: `Read` of `sota-code-security/rules/22-constant-time-comparison.md`.
- treatment **t11**: a content `Grep` for `DSAR|export` over `sota-privacy-compliance/rules/03`.
- treatment **t15**: a content `Grep` for `idempoten` over `sota-api-design/rules/01`.

Three of the six came through Bash or Grep. v5's `Read`-only primary would have scored those runs
as never reaching a rule. The content measure exists for exactly this case, and its positives are
real reads.

The other 14 treatment runs that invoked `sota-python` received the hook's list of its eight rules
files by absolute path and opened none of them.

## What this says

The hook fixed the step it states as one action, and not the step that asks for a judgement.
- Told "invoke `sota-python`" right after the router loaded, the model did it 18 times out of 20.
- Told "read the ones whose topic matches the work", with the paths in hand, it read rules in 4.

v5 showed that index text does not carry the model to the next file. v6 shows that a mechanical
nudge does, but only one file deep and only for a named action.

There are two readings, and v6 cannot tell them apart:

1. **The judgement step is where the chain breaks.** If so, a hook that names one specific rules
   file, or a Stop-time check that an Audit checklist was read, would move it.
2. **The model correctly decides it does not need the rules for these tasks.** hidden_pass is 1.00
   in every arm of v4, v5 and v6, so nothing here shows that reading a rule would have changed an
   outcome.

Separating them needs tasks where a typical agent fails without the rule. This report does not
claim that reading the rules would improve outcomes.

Cost: the hook added 3.5 turns and about 5% per run.

## Notes

- Control read rules in 2/20 here and 0/20 in v5's control, on the same router. Under v5's metric
  this file's control is 1/20 (t10). That comparison crosses days and instruments and is not
  interpreted.
- Before the gates, the driver script called `python -m agent_evals.cli`. That only imports the
  module: it exits 0 and prints nothing, even for `--help`. It was caught because no log and no
  output directory appeared, and fixed to `python -m agent_evals`. No run was made through it.

## Deviations

None. Nothing changed after the pre-registration was committed.

## Spend

| reading | account usage | note |
|---|---|---|
| before the gates, 2026-10-10 21:13 CEST | $865.4539 | (also v5's settled second reading) |
| 2026-10-10 21:47 CEST | $880.7436 | +$15.29, gates and pilot included; the counter lags |
| second reading, hours later | **pending** | |

The SDK estimate is $17.52 for the 40 runs, plus $0.23 preflight, $0.04 sandbox-probe and $0.81
pilot. The account figure is the budget of record, and it is reported once two readings agree.

## Limits

- n = 20 per arm, one sample per case, one model, one language (every case is Python). With
  control at 2/20, treatment needs 8/20 for p < 0.05 (p = 0.032; 7/20 gives 0.064).
- The content measure sees rules text that arrived in a tool result. Text the model received
  some other way is not counted. In these runs, no other way delivered rules text: skill loads
  carry only `SKILL.md` lines, which are excluded, and the hook carries paths only.
- The transcripts (21 MB) stay in the git-ignored `results/v6-2026-10-10/transcripts/`, not in this
  directory.
