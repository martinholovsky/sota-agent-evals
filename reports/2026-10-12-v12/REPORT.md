# v12 measurement — 2026-10-12

**Relative links instead of skill names do not get agents to the right rules file. They remove the
filename guessing, and agents follow them, but they follow the links the router itself carries, which
are not the files the task needs.**

- **Primary, by the frozen rule: NULL.** A cited rules file was reached in **5/20 → 6/20** runs (+0.05;
  3 cases up, 2 down; sign test p = 0.5), against v7's `installed` rows.
- **Secondary, rule tests: NULL.** 0.698 → 0.679 (−0.019, 0 up, 1 down, p = 1.0).
- **Validity and manipulation: passed.** The linked router reached 20/20 runs and no control run. Two
  routers, one per arm. 0 errors, 0 exclusions. Spec tests 20/20 in both arms.

Pre-registration: [PRE-REGISTRATION-v12.md](../../PRE-REGISTRATION-v12.md), frozen at `1ee036b`.

## Configuration

| | |
|---|---|
| model, SDK, limits | as v7: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case |
| treatment root | SOTA-skills `f9de23f` + `tools/linkify.py`: 4,081 pointers rewritten as relative links, visible text unchanged, `skills/` tree `c127f728…`, router `8ec08de83a3c950e` |
| treatment | `installed+links`, 20 runs: `w01`–`w10` 11:21–11:28 CEST, `w11`–`w20` 11:28–11:35, concurrency 2 |
| control | v7's 20 `installed` rows (same `skills/` and `install.sh` minus the links), annotated by `analyze --annotate-reach` |
| gates | preflight PASS ($0.23), sandbox-probe PASS ($0.04), pilot `w07` PASS ($0.25): `links_router` = 1. Not analysed |
| harness | sota-agent-evals `bb88b6c`, 152 tests |

## Results

| | v7 `installed` (names) | **v12 `installed+links`** |
|---|---|---|
| cited rules file reached | 5/20 | **6/20** |
| runs past the router | 8/20 | 11/20 |
| failed rules-file Reads (guessed names) | 2 | **0** |
| mean rules lines seen per run | 26.8 | 136.8 |
| rule tests passed | 37/53 = 0.698 | 36/53 = 0.679 |
| runs passing all rule tests | 12/20 | 11/20 |
| spec tests passed | 20/20 | 20/20 |
| mean cost per run (SDK) | $0.366 | $0.393 (+7%) |
| mean turns | 19.4 | 20.5 |

Cases that changed on reach: up `w05`, `w06`, `w15`; down `w01`, `w09`.

## Where the links led

Read from the transcripts (`h/route.py`, descriptive):

- **Links are followed, and skip a level.** Runs went from the router straight to a rules file without
  loading the skill (`w05`, `w06` opened `sota-code-security/rules/02-authentication.md`; five runs opened
  `sota-shell-scripting/rules/06-ad-hoc-commands.md`). With names, a run had to load a skill or list a
  directory first.
- **They follow the router's own links.** The files opened are the ones the router's principles and
  cross-cutting rules link to (shell-scripting/06 from principle 3, code-security/02 from the identity
  rule), whether or not the task touches them. The router does not link from the task to the file the
  task needs, so a link cannot carry the agent there. `w05` and `w06` reached their cited file, and it
  is one the router itself links (`sota-code-security` rules/02, in its identity rule).
- **The guessing stopped.** 0 failed reads, against 8 across v6–v11, all of them guessed filenames for
  `sota-shell-scripting` rules/06.
- **Most runs still stop at the router.** 9 of 20 opened nothing beyond it (12 of 20 with names).

## What this says

1. **The pointer's form is not what limits reach.** A link is cheaper to follow than a name and is
   followed, but which file it leads to is decided by where the link sits. The file the task needs is
   chosen by matching the task (or the code, v9's hook: 18/20) — not by any pointer in the router.
2. **Links still remove a real defect.** Guessed filenames fail, and a link cannot. On that ground alone,
   unifying on relative links is worth doing; it should not be claimed to improve rule application.
3. **Cost is small.** +12% router bytes; +7% cost per run.

## Limits

- n = 20, one sample per case, one model, Python only. Reused control from about 34 hours earlier.
- Two invocations at concurrency 2 (control: one at 4).
- The rewrite links every pointer at once; a router-only or deep-only variant was not tested.
- Routes are read from the transcripts, not scored.

## Deviations

1. The first launch of the main run passed its arguments as one word (a zsh no-word-split slip in the
   driver line) and exited at argument parsing; no run started and nothing was spent. Relaunched
   unchanged at 11:21.

## Spend

| reading | account usage | note |
|---|---|---|
| 2026-10-12 11:18 CEST | $959.1445 | before the gates |
| 2026-10-12 11:36 CEST | $966.0374 | +$6.89; **first reading, the counter lags** |

SDK estimate: $7.85 for the 20 runs (max $0.63 for one run), plus $0.52 for the gates and pilot. Credit
left at 11:36: $8.96 (auto top-up on).
