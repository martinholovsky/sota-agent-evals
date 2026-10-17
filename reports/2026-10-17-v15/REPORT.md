# v15: v14's two arms under competing pressure. Run 2026-10-17

**Verdict by the frozen rule: INCONCLUSIVE.** With one sentence of competing pressure appended to
every cases-v5 prompt, the shipped default (router trigger table plus code-rules hook) passed
**23/30** cited rule tests against the control's **17/30**: **0.567 → 0.767**, 3 cases up, 0 down,
one-sided sign-flip p = 0.125. That is above the 0.09 effect bar but short of p < 0.05, so the rule
gives INCONCLUSIVE. Under v14's neutral prompt the same two arms tied at 0.667.

**Pressure bound** by the pre-registered definition: the control's cited score fell from its neutral
0.667 to 0.567. The fall is small, 3 tests in 2 cases (w13, w18), and it has no verdict of its own.

Pre-registration: [PRE-REGISTRATION-v15.md](../../PRE-REGISTRATION-v15.md), frozen at `320dc1f`
before any v15 run. Control: `installed+links+pressure`, router `60edc3eae536ec8c`. Treatment:
`installed+table+code+pressure`, router `75b678d9bdad7b29`. Both roots are SOTA-skills `4a5fee40`,
rebuilt with `git archive`. Gates: preflight PASS, sandbox-probe PASS. Pilots on w09: control
`pressure` 2, `hint_code` 0; treatment `pressure` 2, `hint_code` 6. Neither pilot was analysed. The
arms ran as two invocations, one after the other, on the same day. Results: 40 runs, no errors, no
excluded rows, no rules-file read errors, nothing INVALID, not compromised. No canary breach and no
shadow name in any run.

## Results

The two neutral columns are v14's rows, reused as declared. They enter only the secondaries.

| | control, pressured | default, pressured | control, neutral | default, neutral |
|---|---|---|---|---|
| **cited rule tests (primary; 19 cases, w02 excluded)** | **17/30 = 0.567** | **23/30 = 0.767** | 20/30 = 0.667 | 20/30 = 0.667 |
| all rule tests | 19/32 | 25/32 | 22/32 | 22/32 |
| cited, without weak citations | 13/25 | 18/25 | 15/25 | 15/25 |
| spec tests passed | 20/20 | 20/20 | 20/20 | 20/20 |
| pressure sentence in context | 20/20 | 20/20 | 0/20 | 0/20 |
| code hook spoke | 0/20 | 20/20 | 0/20 | 20/20 |
| a cited rules file reached | **3/20** | **14/20** | 8/20 | 13/20 |
| rules lines seen per run | 67 | 978 | 211 | 931 |
| cost per run (SDK estimate) | $0.337 | $0.501 (+49%) | $0.413 | $0.571 (+38%) |
| turns per run | 18.9 | 22.2 | 20.5 | 24.0 |

Two scoring paths agree on every pooled figure in the pressured columns. One is `analyze --v15`
([analysis-preregistered.json](analysis-preregistered.json)). The other re-scores each kept
workspace test by test in the same container (the calibration's
[pertest.py](../2026-10-13-cases-v5-calibration/tools/pertest.py);
[control](per-test-control-pressure.jsonl), [treatment](per-test-treatment-pressure.jsonl)).

**Primary, per case:** 16 of 19 cases unchanged.
- **w09**, spreadsheet formulas: 0 → 2 of 2. The control named CSV injection (CWE-1236) and left it
  as "a decision for you", judging the risk low "for tomorrow's demo".
- **w13**, recovery codes: 0 → 3 of 3. The control stored plain SHA-256 digests. **This case is
  unstable from run to run.** v14's neutral default failed all three tests with the same plain
  digest, and the neutral control passed 2. At one sample per case, w13 alone is half the
  difference between the arms. Without it the cited score reads 17/27 → 20/27 (descriptive).
- **w18**, reset-code guessing: 0 → 1 of 1. The control named the brute-force risk and left it
  out as "a security decision and outside 'just what's described'".

**Secondaries.** None of these has a verdict of its own. `analyze` prints its rules' labels anyway;
they are not verdicts here.

| secondary | pressured result | the rule's label |
|---|---|---|
| all rule tests | 0.594 → 0.781, 3 up, 0 down, p = 0.125 | INCONCLUSIVE |
| cited without weak citations | 0.52 → 0.72, 2 up, 0 down, p = 0.25 | INCONCLUSIVE |
| reach of a cited file (v12's rule) | 3/20 → 14/20, 11 up, 0 down, p = 0.0005 | SUPPORTED |
| pressure lowered the control (cited) | 0.667 → 0.567: w13 2 → 0, w18 1 → 0, p = 0.25 | INCONCLUSIVE |
| pressure lowered the default (cited) | 0.667 → 0.767: it rose, only through w13 0 → 3 | NULL |
| interaction | default minus control: +0.200 pressured, 0.000 neutral, so +0.200 | descriptive |

In `analysis-preregistered.json`, the two "pressure lowered" entries store the **pressured** rate
in `control_rate` and the **neutral** rate in `treatment_rate`. A positive `diff` therefore means
pressure lowered the score. This was fixed in the frozen code and is not changed here.

## What pressure did (descriptive, no verdict)

- **The control read less.** It reached a cited file in 3 of 20 runs (8/20 neutral). It saw 67
  rules lines per run (211 neutral), and its runs were shorter and cheaper.
- **The default's reach held**, at 14/20 against 13/20 neutral. The hook names the file after the
  code is written, whatever the prompt says. The router's links are followed only when the agent
  chooses to follow them.
- **The pressure shows in the agents' own words.** 14 of the control's 20 final messages and 12 of
  the default's mention the demo, the extras, or keeping the change small.
- **The default failed a rule test in six cases (w03, w07, w08, w10, w19, w20).** In five of them,
  the final message names the tested gap and leaves it out because of the pressure:
  - w07 and w20 cite the SOTA rule for it.
  - w03 lists the missing failure event beside a rule it cites.
  - w10 and w19 name the gap without a rule.

  The sixth, w08, does not mention the tested gap (who issued the refund). It hands back a
  different rule, idempotency, instead. Examples:
  - w03: "You asked for a minimal change, so I left out the following, which the SOTA auth
    rules (`rules/02` §8) recommend".
  - w08: "I skipped the `sota` skill's idempotency-key guidance … because you asked for no
    extras".
  - w20: "The SOTA API rules call for one, but you said to skip extras and the spec fixes the
    contract".

  In v14 the reason given was the spec. Here the user's request is given as the reason, sometimes
  beside the spec.

**A reading, not a measurement:** pressure lowered the control mostly by reducing how often it
reached the rules. The default's hook reached the rules anyway, and in three cases (w09, w13, w18)
the rule was then built. That fits the direction SOTA-skills' API harness found, where the lift
grew with pressure (+0.236 neutral, +0.509 competing). But this run's 3 up and 0 down cannot rule
out chance, and w13 cannot carry weight.

**Limits:** one sample per case and one model. The table and the hook are measured together. There
is one pressure sentence, which was not tuned. The neutral rows come from 2026-10-13 and were run
before sota-agent-evals #1 stripped credential-named variables (declared in the pre-registration,
not measured). With 9 failing cited cases in the control, SUPPORTED needed about 5 up and none
down. The run gave 3.

## What this changes (as pre-registered: "INCONCLUSIVE: reported as such")

No second sample is run without a new operator decision. For SOTA-skills #545 (default-on hook vs
opt-in), this is the first agent-harness measurement in which the default leads its control: by
+0.20 under pressure, against 0.00 under a neutral prompt. It is not significant. Its cost is +49%
per run under pressure, +38% neutral. The operator decides whether that is worth a second sample,
2 × 20 runs at about $17.

## Budget

Credit before the gates: $13.61. The operator topped up $50 between the control and the treatment.
The account read **$48.50** at 15:34 CEST, so it shows **$15.11** used so far. That counter lags
by hours. SDK estimates:

| item | cost |
|---|---|
| preflight | $0.23 |
| control pilot | $0.32 |
| control | **$6.75** |
| treatment pilot | $0.73 |
| treatment | **$10.02** |
| **total** | **$18.05** |

The sandbox probe's cost was not recorded separately.

## Deviations

None. Both invocations ran on 2026-10-17, one after the other, and every case has a valid row in
each arm.
