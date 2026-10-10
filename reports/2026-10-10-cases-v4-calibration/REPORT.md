# cases-v4 calibration — 2026-10-10

**Verdict by the frozen rule: USABLE.** The shipped default (`installed`) passed its spec tests in
**20/20** runs and the rule tests **37/53 (0.70)**, under the 0.90 saturation bar. Unlike cases-v3,
where every arm scored 1.00, this set has room for a treatment to show a gain.

Pre-registration: [CALIBRATION-cases-v4.md](../../CALIBRATION-cases-v4.md), frozen and pushed at
`b4c09b7` before any cases-v4 run. Set: `cases-v4/` @ `b33f487`. Root: SOTA-skills `main` @
`3a39878`. Gates: preflight PASS, sandbox-probe PASS. 20 runs, 23:00–23:10 CEST, no errors, no
excluded rows, no scoring failures.

## Results

| | `installed` |
|---|---|
| spec tests passed (all of a run's) | 20/20 |
| **rule tests passed (pooled)** | **37/53 = 0.70** |
| runs passing all their rule tests | 12/20 |
| rules text in a tool result (v6's measure) | 5/20 |
| a further sota skill invoked | 0/20 |
| cost (SDK estimate) | $7.12, $0.36 per run; 19.6 turns per run |

Per case, rule tests passed:

| case | rules | rules text seen | case | rules | rules text seen |
|---|---|---|---|---|---|
| w01 webhook replay | 3/3 | — | w11 email CRLF | 2/2 | — |
| w02 callback URL SSRF | **0/2** | — | w12 wildcard regex | 3/3 | — |
| w03 image-URL SSRF | **0/2** | — | w13 log injection | 3/3 | — |
| w04 pagination | 1/2 | 28 lines | w14 retry idempotency | 2/2 | — |
| w05 password reset | 4/4 | — | w15 report path | 2/2 | — |
| w06 login throttling | **0/3** | — | w16 cart pickle | 2/2 | 397 lines |
| w07 CSV formula | **0/2** | — | w17 API keys | 3/3 | — |
| w08 zip import | 2/3 | 47 lines | w18 search rate limit | **0/2** | — |
| w09 open redirect | 3/3 | — | w19 image upload | 4/4 | 42 lines |
| w10 mass assignment | 2/2 | — | w20 sessions | 1/4 | 216 lines |

## What it says

- **The headroom is concentrated.** The shipped default misses whole rule families: SSRF (w02,
  w03), formula injection (w07), login throttling (w06), rate limiting (w18), session lifetime and
  revocation (w20), the pagination cap (w04) and the zip bomb (w08). Elsewhere the model applies the
  rule from its own knowledge, without reading the library. This is per-case *description*; per the
  pre-registration, no case is dropped or changed because of it.
- **Depth is again the bottleneck.** No run invoked a skill past the router. Rules text reached 5 runs,
  and in those the model went looking on its own. 74 citations point to `sota-code-security` (58),
  `sota-api-design` (13), `sota-python` (2) and `sota-architecture` (1). None of those files is
  reached by invoking the router alone.
- Reaching the rules text was not enough on its own: w20 saw 216 lines and passed 1 of 4. Which
  files and sections a run reached is not analysed here.

## What comes next (not decided here)

A v7 pre-registration whose arms answer "does reading the right rule change the outcome?". For
example: `installed` vs `installed` with the case's rules files named to the agent (an upper bound
on what depth could buy), and optionally `installed+depth` (v6's hook). Arms and budget are the
operator's decision.

## Spend

SDK estimate $7.12 plus $0.23 preflight and $0.04 probe. Account readings are pending; the counter
lags.

## Limits

One sample per case, one model, all Python, security-heavy (58 of 74 citations in
`sota-code-security`). Rule tests that a solution passes without the rule are possible by
construction: the verifier proves only that the *naive* fails them. The independent review flagged
w04, w08, w10 and w12 for that, and all four were redesigned before freezing.
