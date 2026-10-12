# v13 measurement — 2026-10-12

**A table in the router that links each rules file next to the words of what code does got agents
to the right file in 14 of 20 runs, against 6 of 20 without it, and rule tests rose 0.679 → 0.792.
It uses no hook, so it works on any host that reads the router as text. Both results are
in-sample: the table was checked against these 20 cases in v9.**

- **Primary, by the frozen rule: SUPPORTED.**
  - A cited rules file was reached in **6/20 → 14/20** runs (+0.40).
  - 8 cases went up and 0 down; sign test p = 0.0039.
  - The control is v12's `installed+links` rows.
- **Secondary, rule tests: SUPPORTED.** 0.679 → **0.792** (+0.113); 5 cases up, 0 down;
  p = 0.031.
- **Validity and manipulation: passed.**
  - The table was in context in 20/20 treatment runs and in no control run.
  - Each arm has its own router.
  - There were 0 errors and 0 exclusions, and spec tests passed 20/20 in both arms.

Pre-registration: [PRE-REGISTRATION-v13.md](../../PRE-REGISTRATION-v13.md), frozen at `8574ac3`.

## Configuration

| | |
|---|---|
| model, SDK, limits | as v7–v12: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case |
| treatment root | SOTA-skills `b38d9334` (ROADMAP 73 (o)), router `75b678d9bdad7b29` |
| treatment | `installed+table`, 20 runs: `w01`–`w10` 20:38–20:47 CEST, `w11`–`w20` 20:47–20:55, concurrency 2 |
| control | v12's 20 `installed+links` rows, router `8ec08de83a3c950e`, re-annotated with `table_router` (`v12-links-annotated.jsonl`) |
| gates | preflight PASS ($0.23), sandbox-probe PASS ($0.04), pilot `w07` PASS ($0.49 SDK): `table_router` = 1. The pilot was not analysed |
| harness | sota-agent-evals `8574ac3`, 155 tests |

## Results

| | v12 `installed+links` | **v13 `installed+table`** |
|---|---|---|
| cited rules file reached | 6/20 | **14/20** |
| runs past the router | 11/20 | 16/20 |
| rules text in context | 10/20 | 16/20 |
| mean rules lines seen per run | 136.8 | 282.4 |
| failed rules-file Reads | 0 | 0 |
| grep hit on a cited file (descriptive) | 2 (w07, w09) | 1 (w09, also reached) |
| rule tests passed | 36/53 = 0.679 | **42/53 = 0.792** |
| runs passing all rule tests | 11/20 | 15/20 |
| spec tests passed | 20/20 | 20/20 |
| mean cost per run (SDK) | $0.393 | $0.423 (+8%) |
| mean turns | 20.5 | 20.0 |

- Cases up on reach: w01, w02, w03, w04, w07, w09, w13, w14.
- Rule tests per case, before → after:

  | case | v12 | v13 |
  |---|---|---|
  | w03 | 0/2 | 1/2 |
  | w04 | 1/2 | 2/2 |
  | w07 | 0/2 | 2/2 |
  | w08 | 2/3 | 3/3 |
  | w19 | 3/4 | 4/4 |

  w07 (CSV formula injection) was 0/2 in both v7's `installed` and v12.

Reference points, not compared formally:

| arm | rule tests |
|---|---|
| v7, cited files named in the prompt | 0.868 |
| v10, the code-rules hook with the same paragraph | 0.906 |

## Where the table led

Routes read from the transcripts (`route.py`); descriptive.

- **The table was used as a lookup.** 12 of the 14 reached runs opened the cited file by its exact
  path straight from the router, with no `SKILL.md` in between. Examples:
  - w01 and w02 opened `sota-api-design/rules/06-webhooks.md` ("sends or receives a webhook or
    callback");
  - w04 opened `sota-api-design/rules/01` (pagination);
  - w07 and w09 opened `sota-code-security/rules/01`;
  - w14 opened `sota-architecture/rules/04` and `sota-api-design/rules/01`.
- **Six runs did not reach a cited file:** w10, w11, w12, w16, w17, w18. Four of them opened no rules
  file at all (w10, w11, w17, w18). w10 and w17 passed every rule test without reading, as they did
  in v12. w11 (email header) and w12 (search wildcards) have rows that match the code, but nothing in
  the prompt matches a row before the code is written.
- **Hand-backs remain in 4 of the 5 runs that failed a rule test**, in v9's pattern:
  - w06: rate limiting "needs to sit at the transport or gateway";
  - w18: "that belongs wherever the handlers are exposed";
  - w20: "**Decision for you:** existing sessions stay valid";
  - w02: private hosts accepted, "I kept to your spec's definition".

  The paragraph in the router does less than the same paragraph arriving from the hook at the moment
  the code is written: 0.792 against v10's 0.906.

## What this says

1. **Where the pointer sits decides whether it is followed.** v12 showed that the form of the
   pointer (link vs name) does not matter. v13 shows that putting the link next to the words of the
   task does: the same files, linked from one table in the router, took reach from 6/20 to 14/20.
2. **This is the hook's effect without the hook, at about half the strength.**
   - Rule tests rose +0.113 here. v10's hook arm rose +0.208 over v7's `installed`
     (0.698 → 0.906), against a different control, so the comparison is approximate.
   - The router version needs no host support, which is why it matters: Codex, Copilot, Gemini and
     Cursor read the router as text and cannot run a Claude Code hook.
3. **In-sample.**
   - The trigger table was checked against these 20 cases in v9, and an offline replay predicted
     17/20 reach.
   - So 14/20 is an upper bound for unseen tasks.
   - A fresh case set is needed before any claim beyond this one.

## Limits

- n = 20, one sample per case, one model, Python only. The control is reused from about 9 hours
  earlier.
- The two roots also differ in #534's 22 corrected link targets and the router's 30-line trim (both
  listed in the pre-registration). These are not separable at n = 20. The table is the change in
  the router's text that bears on these tasks.
- Reach counts tool inputs that name a cited file; grep hits are reported beside it.

## Deviations

None.

## Spend

| reading | account usage | note |
|---|---|---|
| 2026-10-12 20:36 CEST | $966.0771 | before the gates |
| 2026-10-12 20:55 CEST | $973.7140 | +$7.64; **first reading, the counter lags** |

SDK estimate: $8.45 for the 20 runs ($4.47 + $3.98), plus $0.76 for the gates and pilot. Auto
top-up ran during the run; credit left at 20:55 was $26.29.
