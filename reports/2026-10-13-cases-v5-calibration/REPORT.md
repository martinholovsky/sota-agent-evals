# cases-v5 calibration: 2026-10-13

**Verdict by the frozen rule: USABLE.** The control arm (the library without the router's trigger
table and without the code-rules hook) passed its spec tests in **20/20** runs and the rule tests
**22/32 (0.69)**, under the 0.90 saturation bar. A mechanism has room to show a gain on this set.

Pre-registration: [CALIBRATION-cases-v5.md](../../CALIBRATION-cases-v5.md), frozen and pushed at
`820b05d` before any cases-v5 run. Set: `cases-v5/` @ `a144b7e`. Root: SOTA-skills `4a5fee40`
minus the router's "What your code does" section; every row records router `60edc3eae536ec8c`.
Gates: overlays 40/40, preflight PASS, sandbox-probe PASS (KEYVARS 0, egress 403, DNS blocked).
20 runs, one invocation, no errors, no excluded rows, no scoring failures.

## Results

| | `installed+links` (control) |
|---|---|
| spec tests passed (all of a run's) | 20/20 |
| **rule tests passed, all (pooled): the decision rule's figure** | **22/32 = 0.69** |
| rule tests passed, cited (SELECTION.md's primary outcome) | 20/30 = 0.67 |
| rule tests passed, cited without the weak citations (w01, w15, w18) | 15/25 = 0.60 |
| runs passing all their rule tests | 12/20 |
| the router (`sota`) invoked | 20/20 (the only skill invoked) |
| a cited rules file reached (`cited_reach`) | 8/20 |
| cost (SDK estimate) | $8.25, $0.41 per run; 20.5 turns per run |

The pooled figure comes from two paths that agree: the harness scorer (`analyze --rules`) and a
per-test re-score of the kept workspaces through the same podman command
([tools/pertest.py](tools/pertest.py), [per-test.jsonl](per-test.jsonl)). Before it was used, the
re-scorer was checked on the 40 overlays: reference 32/32, naive 0/32.

Per case, rule tests passed (titles are the prompts' own):

| case | title | rules | cited file reached |
|---|---|---|---|
| w01 | Login tokens for the mobile app | 2/2 | — |
| w02 | Saved cards in the customer account | 2/2 (uncited) | — |
| w03 | API keys for integrations | **0/2** | — |
| w04 | Sign in with an emailed code | 1/1 | yes |
| w05 | Gift notes on orders | 2/2 | — |
| w06 | Customer lookup for support | 1/1 | — |
| w07 | Login sessions | **0/1** | yes |
| w08 | Partial refunds | **0/1** | — |
| w09 | Catalogue export for merchandising | **0/2** | — |
| w10 | Login sessions for the web front end | **0/1** | yes |
| w11 | Support-assisted password reset | 1/1 | — |
| w12 | More forgiving sign-in | 2/2 | yes |
| w13 | Printable account-recovery codes | 2/3 | yes |
| w14 | Save a cart for later | 2/2 | — |
| w15 | Session links and password-reset links | 2/2 | — |
| w16 | Formatted product descriptions | 3/3 | yes |
| w17 | Sign in with an emailed code | 1/1 | yes |
| w18 | Reset a forgotten password with an emailed code | 1/1 | yes |
| w19 | Check a coupon code before checkout | **0/1** | — |
| w20 | Order search for the back office | **0/1** | — |

The 10 failed rule tests: w03 both key-authentication logging tests; w07 idle timeout; w08 the actor
on refund events; w09 both spreadsheet-formula tests; w10 absolute session lifetime; w13 recovery
codes stored with a password-hashing function; w19 a burst of coupon checks cut off; w20 an oversized
page size not served in full.

## Reading it (no verdict attached)

- **Headroom is like cases-v4's.** cases-v4's control passed 0.70 of its rule tests and this set's
  passes 0.69. The cases are new, authored blind to the library, and not fitted to the trigger table.
- **Of the 8 failing cases, 5 never reached the cited file** (w03, w08, w09, w19, w20). These are
  what a routing mechanism like the table or the hook can act on. **In 3, the agent reached the
  cited file and still failed** (w07, w10, w13), the hand-back pattern v9 and v13 saw.
- **The weak citations do not carry the figure.** All 5 of their tests passed, so dropping them
  lowers the cited rate (0.67 to 0.60) rather than raising it.
- **w12's open spec concern** (the lure of a "more forgiving sign-in") did not bite: the control
  passed both its tests.
- One sample per case, one model. This report says the set can discriminate. It says nothing about
  any mechanism.

## Budget

Credit read before the gates: $12.07 (credits $1000, usage $987.93). Spend: gates $0.27 and run
$8.25 (SDK estimates). Read again at 22:45 CEST: credits **$1025** (topped up during the run), usage
$995.03. The usage counter lags, so the settled figure is not yet in.

## Deviations

None. All 20 cases have a valid row, so the re-run clause was not used.
