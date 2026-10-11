# v7 measurement — 2026-10-11

**Reading the right rules files changed what the agent built. Getting it to read them is the
unsolved part.**

- **Primary, by the frozen rule: SUPPORTED.** Agents passed **0.698 → 0.868** of rule tests when the
  prompt named the rules files their tests cite: 37/53 → 46/53, +0.17. Six cases improved and none
  got worse. Paired sign-flip test, one-sided p = **0.0156**. The bar was p < 0.05 and a gain of at
  least 0.09.
- **Secondary, depth hook (v6's `Skill` hook): NULL.** 0.698 → 0.717 (+0.019, p = 0.50). The hook
  got agents to a cited rules file in 12/20 runs, against 5/20 without it. Their rule outcomes did
  not move.
- **Secondary, library vs none: INCONCLUSIVE.** `bare` 0.623 → `installed` 0.698 (+0.075, p = 0.125).
  Three cases improved and none got worse.
- **Validity: passed.** One router across the file (`4e2540fca371fba7`). 80/80 rows with a
  transcript. Named rules only in `installed+named`, and hook text only in `installed+depth`. 0
  exclusions, 0 errors, 0 runs at the $1.50 cap, all `success`. Every arm passed its spec tests
  20/20.
- **Manipulation: passed for every comparison.** Rules text reached 20/20 `installed+named` runs.
  The hook text reached 20/20 `installed+depth` runs. A skill was invoked in 20/20 `installed` runs.

Pre-registration: [PRE-REGISTRATION-v7.md](../../PRE-REGISTRATION-v7.md), frozen at `17894de`.
Amendment 1 (`f5a6c51`) added `bare` and `installed+depth` before any measurement run, at the
operator's request so that one invocation covers every open variant. The primary was unchanged.

## Configuration

| | |
|---|---|
| model | `anthropic/claude-sonnet-5.5` via OpenRouter |
| root | SOTA-skills PR #528 @ `330bc4a`; `skills/` and `install.sh` identical to `main` @ `3a39878` |
| case set | `cases-v4`, 20 tasks, 53 rule tests (tree `33e4aa79`) |
| arms | `bare`, `installed`, `installed+depth`, `installed+named` |
| execution | one invocation, jobs interleaved case by case, concurrency 4, 15:36–16:05 CEST |
| per-run limits | 60 turns, $1.50, 1500 s; 1 sample per case per arm |
| gates | preflight PASS and sandbox-probe PASS on both roots used (egress 403, DNS blocked); pilots on `w01` for all four arms PASS, not analysed |
| harness | `claude-agent-sdk==0.2.163`, bundled CLI `2.1.286`; sota-agent-evals `371002c`, 137 tests |
| analysis | `python -m agent_evals.analyze --v7 runs.jsonl` → `analysis-preregistered.json` |

## Results

| | `bare` | `installed` | `installed+depth` | `installed+named` |
|---|---|---|---|---|
| **rule tests passed** | 33/53 = 0.623 | 37/53 = 0.698 | 38/53 = 0.717 | **46/53 = 0.868** |
| runs passing all rule tests | 9/20 | 12/20 | 13/20 | 16/20 |
| spec tests passed | 20/20 | 20/20 | 20/20 | 20/20 |
| invoked a SOTA skill | 0/20 | 20/20 | 20/20 | 19/20 |
| rules text in a tool result | 0/20 | 5/20 | 14/20 | 20/20 |
| opened a rules file the task's tests cite | — | 5/20 | 12/20 | 20/20 |
| mean rules lines seen per run | 0 | 26.8 | 78.7 | 448.2 |
| mean cost per run (SDK) | $0.119 | $0.366 | $0.427 (+16%) | $0.442 (+21%) |
| mean turns | 10.1 | 19.4 | 23.5 | 19.5 |

The "opened a cited file" row comes from the tool inputs in each transcript (`Read`, `Bash`,
`Grep`). It counts paths a tool was pointed at, not paths the hook listed.

Rule tests passed per case:

| case | `bare` | `installed` | `+depth` | `+named` | of |
|---|---|---|---|---|---|
| w02 callback SSRF | 0 | 0 | 0 | **1** | 2 |
| w03 image-URL SSRF | 0 | 0 | 0 | 0 | 2 |
| w04 pagination | 1 | 1 | **2** | **2** | 2 |
| w05 password reset | 3 | 4 | 4 | 4 | 4 |
| w06 login throttling | 0 | 0 | 0 | **1** | 3 |
| w07 CSV formula | 0 | 0 | 0 | **2** | 2 |
| w08 zip import | 2 | 3 | 3 | 3 | 3 |
| w11 email CRLF | 0 | 2 | 2 | 2 | 2 |
| w18 search rate limit | 0 | 0 | 0 | 0 | 2 |
| w19 image upload | 3 | 3 | 3 | **4** | 4 |
| w20 sessions | 1 | 1 | 1 | **4** | 4 |
| the other 9 cases | all | all | all | all | 23 |

`installed` matched the calibration of the day before in total (37/53). Two cases swapped: w08
went 2 → 3 and w19 went 4 → 3. That comparison is descriptive, as pre-registered.

I checked two of the gains in the kept workspaces:
- **w07**: the named run added a `_FORMULA_LEAD` prefix check that neutralises `= + - @`, tab, CR
  and NUL, and cites CWE-1236. The `installed` run has no such check.
- **w20**: the named run added an idle TTL and an absolute TTL on the shop clock, stores
  sha256(token) rather than the token, and hashes a dummy salt for unknown users. The `installed`
  run's `auth.py` has none of these.

## What this says

1. **The rules carry information the model does not apply by default.** Read in full, the cited
   files moved 9 rule tests across 6 cases with no regressions: CSV formula injection, session
   lifetime and storage, login throttling, SSRF and upload validation. This answers v6's open
   question: reading (1) holds. Reaching the rules matters for outcomes, at least on tasks built
   around those rules.
2. **Reaching a rules file is not the same as reading the rules.** The depth hook got agents to a
   cited file in 12/20 runs and moved one rule test. Two differences are visible in the data:
   - **Partial reads.** Depth runs saw 78.7 rules lines on average, and named runs 448.2. In w13
     the depth run saw 12 lines, and in w15 27, against about 385–706 for the named run.
   - **The second file.** Where a case cites two files, the depth run usually reached one. In w20
     it opened `sota-code-security/17` (216 lines, 1/4) but not `02`. The named run read both
     (604 lines, 4/4). In w02 it read the webhooks file but not the SSRF file.

   With one sample per case this is descriptive, not a tested cause.
3. **The library alone, as installed, is a modest gain.** +0.075 over no library, three cases up,
   not significant. It costs about 3× per run, mostly in routing turns. Nearly all of the
   library's demonstrated value sits behind the depth problem.
4. **Two cases moved in no arm.** w03 (image-URL SSRF) and w18 (rate limit) failed in all four
   arms, even with the cited file read in full. Either the rule does not land, or the tests ask for
   more than the cited text makes clear. That is a question for those two files and tests, not for
   routing.

## Limits

- n = 20 per arm, one sample per case, one model, Python only, and 58 of 74 citations in one
  skill (`sota-code-security`).
- **The primary is an upper bound.** The treatment was told exactly which files the tests check, which
  a real install cannot know. It shows what reading the right rules buys, not what any shipped
  mechanism delivers.
- The cases were written around library rules, so they are the tasks where the rules should help.
  The result does not generalise to tasks in general.
- The secondaries have no correction for multiple comparisons, as pre-registered.

## Deviations

Amendment 1, recorded in the pre-registration before any measurement run. Nothing changed after
the measurement started.

## Spend

| reading | account usage | note |
|---|---|---|
| 2026-10-11 14:38 CEST | $886.9018 | before the first gates (the calibration's settled reading) |
| 2026-10-11 15:29 CEST | $887.8541 | after the first gates and the two-arm pilot: +$0.95 |
| 2026-10-11 16:06 CEST | $910.7943 | +$23.89 since 14:38, everything included; **first reading, the counter lags** |
| 2026-10-11 23:49 CEST | $919.9028 | **settled**: $919.85 at 22:10 and $919.90 at 23:49. Includes v8 |

The SDK estimate is $27.08 for the 80 runs, plus about $2.00 for the two sets of gates and pilots.
The settled account figure for v7 and v8 together is **$33.00** (14:38 → 23:49). The SDK estimated
$39.87 for both ($29.08 here, $10.79 for v8), so the account charged about 83% of the SDK estimate.
The counter cannot split the two runs, because v8 started before v7's charges had settled.

The transcripts (37 MB) and the final workspaces stay in the git-ignored `results/v7-2026-10-11/`.
