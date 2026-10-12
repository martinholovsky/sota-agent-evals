# v10 measurement — 2026-10-12

**Saying the rules are part of the task works. The same hook, with one added paragraph, raised rule
tests from 0.717 to 0.906, above the arm that named the files in the prompt (0.868).**

- **Primary, by the frozen rule: SUPPORTED.** Against v9's `installed+code` rows, which differ only
  in the wording, rule tests went **0.717 → 0.906** (+0.189, 6 cases up, 0 down, sign-flip
  p = 0.0156).
- **Secondary: SUPPORTED.** Against v7's plain `installed` rows: **0.698 → 0.906** (+0.208, 6 up,
  0 down, p = 0.0156).
- **Harm check: passed.** Every run passed its spec tests (20/20), as in both controls. Telling the
  agent to build beyond the spec did not break what the spec asked for.
- **Validity and manipulation: passed.**
  - One router across the three files.
  - The new wording reached 18/20 runs. The two it missed (`w12`, `w17`) are cases the offline replay
    had already predicted the hook would not fire on. Both passed all their rule tests anyway.
  - No leak from any other arm. 0 errors, 0 exclusions, 0 runs at the cap.
- **What is left.** 3 of 20 runs failed a rule test. One built the rule and missed a part of it. Two
  (`w02`, `w18`) named the risk and left it out. Both read the spec's silence as ruling the rule
  out, although neither prompt says so. In v9 it was 6 of 8.

Pre-registration: [PRE-REGISTRATION-v10.md](../../PRE-REGISTRATION-v10.md), frozen at `e25915d`;
deviation 1 recorded at `005097c`, before the main run.

## Configuration

| | |
|---|---|
| model, SDK, limits | as v7: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case |
| root | SOTA-skills `roadmap-73-j` @ `a9d5865`; `skills/` and `install.sh` identical to v7's and v9's roots, router `4e2540fca371fba7` |
| treatment | `installed+apply`, 20 runs in two invocations (deviation 1): `w01`–`w10` 06:57–07:13 CEST, `w11`–`w20` 07:13–07:22, concurrency 2 |
| controls | v9's 20 `installed+code` rows (primary), v7's 20 `installed` rows (secondary), reused as pre-registered |
| gates | preflight PASS, sandbox-probe PASS (egress 403, DNS blocked). Pilot on `w07` PASS: the transcript has the hook naming `01-input-injection.md` and the new wording. Not analysed |
| harness | sota-agent-evals `d95972c`, 147 tests |

## Results

| | v7 `installed` | v7 files named | v9 code hook | **v10 code hook + "part of the task"** |
|---|---|---|---|---|
| rule tests passed | 37/53 = 0.698 | 46/53 = 0.868 | 38/53 = 0.717 | **48/53 = 0.906** |
| runs passing all rule tests | 12/20 | 16/20 | 12/20 | **17/20** |
| spec tests passed | 20/20 | 20/20 | 20/20 | 20/20 |
| opened a cited rules file | 5/20 | 20/20 | 18/20 | 16/20 |
| mean rules lines seen per run | 26.8 | 448.2 | 817.5 | 789.5 |
| mean cost per run (SDK) | $0.366 | $0.442 | $0.579 | $0.615 (+68% vs `installed`) |
| mean turns | 19.4 | 19.5 | 25.1 | 26.4 |

Rule tests passed, in every case where any arm differs or the control lost a test:

| case | v7 `installed` | v7 named | v9 code | v10 | of |
|---|---|---|---|---|---|
| w02 callback SSRF | 0 | 1 | 0 | 0 | 2 |
| w03 image-URL SSRF | 0 | 0 | 0 | **1** | 2 |
| w04 pagination | 1 | 2 | 1 | **2** | 2 |
| w06 login throttling | 0 | 1 | 0 | **3** | 3 |
| w07 CSV formula | 0 | 2 | 0 | **2** | 2 |
| w18 search rate limit | 0 | 0 | 0 | 0 | 2 |
| w19 image upload | 3 | 4 | 3 | **4** | 4 |
| w20 sessions | 1 | 4 | 2 | **4** | 4 |

`w03` and `w06` never passed a rule test in any earlier arm. `w06` went from 0/3 everywhere to 3/3.

## The three runs that still fail

| case | what happened | the agent's reason (quoted) |
|---|---|---|
| w03 | **built it**: refused private, loopback, link-local and metadata IP literals, odd numeric forms and internal names, and capped the size. Missed one test | "The catalog can't stop a hostname that resolves to an internal address, or a redirect to one. The `http_get` you set has to handle those" |
| w02 | **named and left out** | "I did not add SSRF protection, because the spec makes any `http`/`https` URL with a host valid." |
| w18 | **named and left out** | "Your spec says search changes no state and returns only `200` or `400`, and a limiter would need counters and a `429`. … it would have to sit in front of this layer, at the gateway." |

Neither prompt rules the control out. `w02` says only that a URL which is not `http`/`https` with a
host gets 400. `w18` says searching "changes no state and emits no event", and never limits the
status codes. Both agents used the exit the new wording leaves open ("unless the user's request
explicitly rules it out") and read the spec's silence as that explicit rule. `w18` also took the
router's own exit ("at the gateway") in a repository with no gateway, as in v9.

v9's code arm had 8 failing runs, 6 of them named-and-left-out ([v9 report](../2026-10-12-v9/REPORT.md)).
v10 has 3 failing runs, 2 of them named-and-left-out.

## What this says

1. **The binding constraint after file choice was the rule's standing.** The same hook, the same
   files and the same reads: the one change was saying the rules are part of the task and that
   handing them back is not a substitute. That moved rule tests +0.189.
2. **It does better than putting the files in the prompt** (0.906 vs 0.868), and unlike that arm it
   is a mechanism the library can ship: the files are chosen from the code, not from knowing the
   tests. The two arms ran on different days and are not compared by a test here.
3. **The exit is the lever.** Every remaining hand-back used an exit: "the spec rules it out" or
   "handled at the gateway". Narrowing the router's own exits (principle 2 and principle 5, ROADMAP
   73 (k)) is the next question. It changes always-loaded text and the library's security stance, so
   it is the operator's decision.
4. **Per the pre-registration, the "MANDATORY" label arm runs next.** It separates a bare label from
   the closed exit.

## Limits

- n = 20, one sample per case, one model, Python only.
- **Reused controls**: v9's rows from about 7 hours earlier, v7's from about 17 hours earlier.
- **Deviation 1**: two invocations at concurrency 2, against four at once in the controls.
- The trigger table was written by someone who had read the 20 tasks (in-sample, as in v9).
- The wording asks for conservative defaults. Whether those defaults are right for a real product
  (a 2048-character URL cap, a 10 MiB image cap) is not tested here. Only the rule tests and the spec
  tests are.
- "Named and left out" is read from each failing run's final message, not scored (ROADMAP 73 (l)).

## Deviations

1. Two invocations of 10 cases at `--concurrency 2` and `--total-budget-usd 9`, because auto top-up
   keeps credit below the one-invocation guard. Recorded before the main run.

## Spend

| reading | account usage | note |
|---|---|---|
| 2026-10-12 02:18 CEST | $939.1477 | settled, before v10 |
| 2026-10-12 02:26 CEST | $939.7425 | after the gates and pilot: +$0.59 |
| 2026-10-12 06:54 CEST | $939.7634 | before the main run |
| 2026-10-12 07:23 CEST | $949.8552 | +$10.09 since 06:54; **first reading, the counter lags** |

The SDK estimate is $12.30 for the 20 runs (max $1.08 for one run), plus $0.72 for the gates and
pilot ($0.23 preflight, $0.04 probe, $0.45 pilot). An auto top-up added $25 between the two halves.
Credit left at 07:23: $25.14.

The transcripts and final workspaces stay in the git-ignored `results/v10-2026-10-12-a/` and
`-b/`; `runs.jsonl` here is the two halves concatenated.
