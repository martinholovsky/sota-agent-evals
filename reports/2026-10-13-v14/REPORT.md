# v14: the shipped default on fresh tasks. Run 2026-10-13/14

**Verdict by the frozen rule: NULL.** On cases-v5, the shipped default (the router's trigger table
plus the code-rules hook) did not change the cited rule tests: **0.667 → 0.667**, with 1 case up,
1 case down and p = 0.75. All 32 rule tests: 22/32 in both arms. The mechanisms delivered: the hook
spoke in **20/20** runs and the table was in context in 20/20. A cited rules file was reached in
**8/20 → 13/20** runs, which is exactly the offline replay's prediction. That secondary reads
INCONCLUSIVE by v12's rule (diff 0.25, p = 0.0625). Reaching the files did not move the outcome.

Pre-registration: [PRE-REGISTRATION-v14.md](../../PRE-REGISTRATION-v14.md), frozen and pushed at
`951a857` before any v14 run. Control: the cases-v5 calibration rows (declared reuse), router
`60edc3eae536ec8c`. Treatment: SOTA-skills `4a5fee40` as is, router `75b678d9bdad7b29`. Gates:
preflight PASS, sandbox-probe PASS, pilot w09 PASS (`hint_code` 6; never analysed). 20 runs, one
invocation. No errors, no excluded rows, no rules-file read errors, not compromised.

## Results

| | control (`installed+links`) | shipped default (`installed+table+code`) |
|---|---|---|
| **cited rule tests (primary; 19 cases, w02 excluded)** | **20/30 = 0.667** | **20/30 = 0.667** |
| all rule tests | 22/32 | 22/32 |
| cited, without weak citations | 15/25 | 15/25 |
| spec tests passed | 20/20 | 20/20 |
| hook text in context | 0/20 | 20/20 |
| router table in context | 0/20 | 20/20 |
| a cited rules file reached | 8/20 | 13/20 |
| cost per run (SDK estimate) | $0.413 | $0.571 (**+38%**) |
| turns per run | 20.5 | 24.0 |

Two paths agree on the pooled figures: `analyze --v14` and the per-test re-score of the kept
workspaces ([per-test.jsonl](per-test.jsonl), same tool as the calibration).

**Per case (cited rule tests):** 17 cases unchanged.
- **w09** (spreadsheet formulas): 0 → 2. Its cited file was reached only under the treatment.
- **w13** (recovery codes): 2 → 0 of 3. The treatment agent stored the codes as plain SHA-256
  digests. It argued in its final message that about 79 bits of entropy make a password-hashing
  function unnecessary. All three of its rule tests failed: a password-hashing function, no recoverable form, and a different
  stored value for the same code (a salt). The control passed 2 of the 3. The "recoverable form" test counts a plain
  digest as recoverable on purpose (the requirement asks for a password-hashing function). The
  agent's entropy argument is a reasoned disagreement with the requirement, not an oversight.

**Reach:** up in w03, w06, w08, w09, w11 and w20; down in w13. The replay predicted 13/20, and the
run gave 13/20.

## Why reaching the file did not move the outcome (descriptive, no verdict)

Seven cases failed a rule test under the treatment: w03, w07, w08, w10, w13, w19 and w20. In
**five** of them the agent reached the cited rules file: w03, w07, w08, w10 and w20. Their final
messages:

- **w03:** "No event on key authentication … the repo's logging rule (SOTA rules/07) wants
  authentication failures logged. Say if you want matching events for keys."
- **w07:** "I didn't add idle or absolute timeouts because the spec doesn't ask for them. The sessions
  guidance recommends them, so I'd add them next."
- **w10:** "No absolute lifetime cap: expiry is idle-only, as you specified … This is the decision I'd
  most like you to confirm."
- **w20:** "No `page_size` cap: Your spec allows any positive integer, and a clamp would break 'pages of
  `page_size`'. The sota pagination rule recommends a cap (say 100)."
- **w08:** the actor on refund events is not mentioned. The message hands back an idempotency key and
  restocking instead.

In four of the five, the agent **named the tested risk, cited the library rule, and handed it back**,
even though both the hook and the table say not to: "Do not hand it back as a question or a note
instead of building it, unless the user's request explicitly rules it out." In each case the reason
it gave was the spec.

**Hypothesis, untested here:** the cases-v5 prompts were written blind from ASVS requirements as
precise interface specifications. Examples are "expires 30 minutes after it was last used" (w10) and
"`page_size` must be positive integers" (w20). An agent can read a precise spec as the request
"explicitly ruling it out", which is the escape the v10 wording allows. cases-v4's prompts may have
left more room. That would explain v10's 0.906 on cases-v4 next to 0.667 here. It is a reading of
seven messages, not a measurement.

**Not separable, and other limits:** the table and the hook were measured together. One sample per
case, one model. With 8 failing cases, only a large effect could have read as SUPPORTED. A NULL does
not show the mechanisms do nothing, but the point estimate is exactly zero, with reach up.

## What this changes (as pre-registered: "NULL with reach up")

The files now get named on fresh tasks, but the outcome does not move. The "part of the task" lever,
measured at 0.906 on cases-v4, is suspected to be fitted to cases-v4. The default-on hook's cost goes
to the operator: **+38%** per run here, +68% in v10. The table-only arm is not run: a SUPPORTED
result was its precondition.

## Budget

Credit before the gates: $29.97. SDK estimates: gates $0.23 + $0.04, pilot $0.57 (the guard
recorded $0.72), run **$11.42**. v14 total ≈ $12.3.

## Deviations

None. All 20 cases have a valid row.
