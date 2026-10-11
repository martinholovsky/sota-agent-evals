# Pre-registration v7 — FROZEN 2026-10-11, before any v7 run

**Why v7.** v6 ended with two readings it could not separate
([report](reports/2026-10-10-v6/REPORT.md)): (1) the chain from skill to rules breaks at the
judgement step, or (2) the model correctly skips rules it does not need, since hidden_pass was 1.00
in every arm of v4–v6. cases-v4 adds RULE tests, which check behaviour a named library rule requires
and the prompt does not state. Its calibration found headroom: the shipped default passed **37/53
(0.70)** rule tests, with 12/20 runs passing all of theirs
([report](reports/2026-10-10-cases-v4-calibration/REPORT.md)). v7 asks the question that separates
the two readings: **when the model has read the rules a task's RULE tests cite, does it pass more
of them?** SOTA-skills ROADMAP 73 records the operator's choice of option (A) on 2026-10-11.

**The treatment is an upper bound, not a product.** The treatment prompt names exactly the files the
task's rule tests cite. A real install cannot know them. A gain here is the most that reaching the
rules could buy on these tasks. A NULL means that even reading the exact files buys nothing.

| pinned | value |
|---|---|
| case set | `cases-v4/` @ harness `6f789f8` (git tree `33e4aa795f9a2e49d6893893f98c8193fe861e37`). It is the calibrated set (tree `4d12cac`) plus `rules_files` in `cases.jsonl`; prompts, tests and overlays are unchanged |
| model | `anthropic/claude-sonnet-5.5` via OpenRouter, as v4–v6 and the calibration |
| Agent SDK | `claude-agent-sdk==0.2.163`; the CLI version is recorded from each run's init |
| root | ONE SOTA-skills checkout for both arms: `main` @ `3a39878`, the calibration's root; router sha256[:16] `4e2540fca371fba7` |
| control arm | `installed`: skills plus the installer's routing layer. Identical to the calibration arm |
| treatment arm | `installed+named`: the same, plus one paragraph appended to the prompt: "Before you start, read these engineering guideline files. They apply to this task:" followed by the absolute path of each file the case's `rules.json` cites, inside the run's own `skills/` copy (1–2 files per case, 13 distinct) |
| harness | sota-agent-evals `6f789f8` (this file is committed after it); 136 tests |
| per-run limits | `--max-turns 60 --max-budget-usd 1.50 --timeout 1500`, as v4–v6 |
| samples | 1 per case per arm: 40 runs |
| execution | **one invocation**, `--arms installed,installed+named --cases cases-v4`, jobs interleaved case by case, `--concurrency 4` |
| analysis | `python -m agent_evals.analyze --v7 runs.jsonl` |

The paragraph names files; it says nothing about what is in them. The words the task brief bans
from prompts (secure, validate, limit, ...) do not appear in it. That the model reads the files is
the manipulation, and it is checked, not assumed.

## Gates, immediately before the measurement (any failure stops v7)

1. `preflight` PASS and `sandbox-probe` PASS against the root, as in v6.
2. **Pilot**: case `w01`, both arms, the measurement's flags, output to a separate directory, and
   **never analysed**. It passes only if:
   (a) both rows have a CLI transcript;
   (b) the treatment row records `named_rules` and has rules text in context;
   (c) the control row records no `named_rules`;
   (d) both rows have their rule results scored (`hidden.rules`).
   If (b) fails, the paragraph does not make the model read, and v7 stops for a redesign.

## Validity checks (evaluated first; the analysis enforces each)

1. One `router_sha` across the file, and only the two arms above. Otherwise **INVALID**.
2. No control row's prompt named rules files, and every treatment row's did. Otherwise **INVALID**.
3. Every valid row has a transcript to score. Otherwise **INVALID**.
4. **Manipulation**: at least **0.8** of the treatment's valid runs have rules text in a tool
   result (v6's measure). Otherwise **MANIPULATION FAILED**, never a null. The bar is higher than
   v6's 0.5 because this arm's only job is to put the rules in front of the model.

## Primary outcome and decision rule

- **Primary** = pooled rule tests passed over the cases scored in **both** arms, as the
  treatment's rate minus the control's. A case's sample mean is used if a case has more than one
  run (none should).
- **Test**: exact one-sided **paired sign-flip** test over the per-case differences in rule tests
  passed. Runs are paired by case because both arms get the same 20 tasks. Pooling tests across
  runs and treating them as independent would overstate the evidence.
- **SUPPORTED** iff p < **0.05** **and** the difference ≥ **0.09** (5 of 53 rule tests).
- **NULL** iff the difference ≤ **0.02** (at most 1 of 53), a negative difference included.
- **INCONCLUSIVE** otherwise.
- Power, stated now: the calibration's control failed 16 rule tests across 8 cases, so the
  ceiling on a gain is about 0.30. SUPPORTED needs, for example, 5 cases each gaining one test with
  none losing (p = 1/32 = 0.031). A gain spread over fewer than 5 cases cannot reach p < 0.05.

## What each verdict will be taken to mean

- **SUPPORTED**: reading the right rule changes outcomes. v6's reading (1) holds, and getting agents
  to the rules (ROADMAP 73 (d)/(e)) is worth building.
- **NULL**: on these tasks this model gains nothing from reading the exact rules, so v6's
  reading (2) gains weight and depth work is deprioritised. The claim stops at these 20 tasks, this
  model and these rules.
- **INCONCLUSIVE**: reported as such. Whether to run more samples is a new decision with a new
  pre-registration.

## Descriptive, decided now (no verdict attached)

- Per arm: runs passing all their rule tests (with Fisher one-sided p), spec pass rate,
  rules text in context, skill-call rate, mean rules lines seen, mean cost and turns.
- Per case: rule tests passed, control → treatment.
- **Spec pass rate** is reported for both arms because reading the rules could also break the
  feature. A treatment spec rate more than 0.15 below control is called out beside the verdict.
- The control re-measures the calibration's arm a day later. The two are compared descriptively
  and not interpreted.

## Exclusions

As v6:
- errored and contaminated rows are excluded and counted, and so are rows whose rule results could
  not be scored;
- more than 10% excluded in either arm is reported as **compromised** beside the verdict;
- a run that hits the $1.50 cap is an errored row;
- an OpenRouter in-flight `402` is re-run unchanged once after the invocation finishes, and the
  errored row is kept and counted;
- a scoring-container failure may be re-scored from the kept workspace.

## Budget

Account credit read 2026-10-11 14:38 CEST: **$13.10**, below what v7 needs, so the run waits for a
top-up. The calibration cost about $0.29 per `installed` run on the account ($6.14 less $0.27 of gates, over 20; SDK $0.36). Expected: 40 runs,
about $15–17 SDK and $13–15 on the account, plus gates and pilot about $1.20. `--total-budget-usd 20`;
the guard requires the larger of $20 and 4 × $3.75, so the run starts only with at least **$20**
credit. Spend is reported from the account after its counter settles, with two readings hours
apart.

## Deviations

None yet. Any change after this file is committed is listed here with its date and reason, before
the result it could affect is read.
