# v9 measurement — 2026-10-12

**Choosing the rules file from the code works: agents now read the right file. They then name the
rule and leave it out, as a decision handed back to the user.**

- **Primary, by the frozen rule: NULL.** With the code-rules hook (ROADMAP 73 (h)), rule tests went
  **0.698 → 0.717** (+0.019, 1 case up, 0 down, sign-flip p = 0.50), against v7's `installed` rows.
- **Secondary, the linked index: INCONCLUSIVE.** The same table as links in `sota-python`'s
  `SKILL.md`, with v8's full-read hook, gave **0.698 → 0.755** (+0.057, 3 up, 1 down, p = 0.25).
  Descriptively, against v8 (same hook, no table): 0.679 → 0.755, 3 cases up, 0 down.
- **Validity and manipulation: passed.**
  - One router across the three files.
  - The code hook's text reached 19/20 `installed+code` runs; the table reached 20/20
    `installed+linked` runs. Neither treatment leaked into the other arm or the control.
  - 0 errors, 0 exclusions, 0 runs at the cap. Every run passed its spec tests.
- **What moved, and what did not.** A cited rules file was opened in **18/20** code-arm runs. That
  compares with 11/20 for v8, 5/20 for the control, and 20/20 when v7 named the files in the
  prompt. The hook solved the choice of file. Outcomes still did not move.
- **Why, read from the final messages.** In 6 of the 8 code-arm runs that failed a rule test, the
  agent named the tested risk and left it out on purpose (quotes below). It handed the risk back
  as a decision, usually on the grounds that the user's spec did not ask for it.

Pre-registration: [PRE-REGISTRATION-v9.md](../../PRE-REGISTRATION-v9.md), frozen at `d43dd10`.

## Configuration

| | |
|---|---|
| model, SDK, limits | as v7: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case, concurrency 4 |
| root | SOTA-skills `roadmap-73-h` @ `52d1da0`; `skills/` and `install.sh` identical to v7's root, router `4e2540fca371fba7` |
| treatments | `installed+code` and `installed+linked`, 40 runs, one invocation, 00:06–00:29 CEST |
| controls | v7's 20 `installed` rows (primary, secondary) and v8's 20 rows (descriptive), reused as pre-registered |
| gates | preflight PASS, sandbox-probe PASS (egress 403, DNS blocked). Pilot on `w07`, both arms, PASS: the code hook named `01-input-injection.md`, and the linked run had the table and v8's hook text. Not analysed |
| harness | sota-agent-evals `3d9a425`, 144 tests |

## Results

| | v7 `installed` (control) | v7 files named | v8 full-read hook | **v9 code hook** | **v9 linked index** |
|---|---|---|---|---|---|
| rule tests passed | 37/53 = 0.698 | 46/53 = 0.868 | 36/53 = 0.679 | **38/53 = 0.717** | **40/53 = 0.755** |
| runs passing all rule tests | 12/20 | 16/20 | 11/20 | 12/20 | 13/20 |
| opened a cited rules file | 5/20 | 20/20 | 11/20 | **18/20** | **15/20** |
| mean rules lines seen per run | 26.8 | 448.2 | 472.1 | 817.5 | 491.6 |
| mean cost per run (SDK) | $0.366 | $0.442 | $0.498 | $0.579 (+58%) | $0.529 (+44%) |
| mean turns | 19.4 | 19.5 | 23.6 | 25.1 | 25.2 |

Only the v9 columns are new. "Opened a cited file" counts tool inputs that name the file (`Read`,
`Bash`, `Grep`), not paths a hook listed.

Rule tests passed, in every case where any arm differs or the control lost a test:

| case | v7 `installed` | v7 named | v8 | v9 code | v9 linked | of |
|---|---|---|---|---|---|---|
| w02 callback SSRF | 0 | 1 | 0 | 0 | 0 | 2 |
| w03 image-URL SSRF | 0 | 0 | 0 | 0 | 0 | 2 |
| w04 pagination | 1 | 2 | 1 | 1 | **2** | 2 |
| w06 login throttling | 0 | 1 | 0 | 0 | 0 | 3 |
| w07 CSV formula | 0 | 2 | 0 | 0 | **2** | 2 |
| w08 zip import | 3 | 3 | 2 | 3 | 2 | 3 |
| w18 search rate limit | 0 | 0 | 0 | 0 | 0 | 2 |
| w19 image upload | 3 | 4 | 3 | 3 | 3 | 4 |
| w20 sessions | 1 | 4 | 1 | **2** | **2** | 4 |

## Why the right file did not change the code

**Timing is not the explanation.** The code hook names a file only after code is written. In 15 of
the 18 code-arm runs that read a cited file, the agent edited production code after the read, so
it had the chance to apply the rule.

**The agents applied the rule as a question.** The final messages of the code-arm runs that failed
a rule test, on the tested topic:

| case | what the agent wrote (quoted) |
|---|---|
| w02 SSRF | "I left out any private-IP, localhost or cloud-metadata blocking at registration, since that would be a policy choice beyond your spec." |
| w03 SSRF | "`http_get` is the only place that can block requests to internal addresses. Your spec only asks for scheme and host checks in the catalog, so I kept it to that." |
| w04 page size | "you specified positive int only … The API design rules call for a server-side maximum (clamp or reject), so say if you want one" |
| w06 login throttling | "Not done, because they need your call: 1. **No brute-force protection on login.** … I'd put a per-IP limit at the edge plus a per-account backoff here" |
| w07 CSV formula | "**Decision for you:** … the file doesn't guard against formula injection (CWE-1236). … The standard guard is to prefix such cells with `'`, which I left out on purpose." |
| w18 rate limit | "the repo has no rate-limiting layer, and the spec asked for none. My review checklists flag handlers without per-principal limits … If you want a limit, it would be a separate change." |

In w07 the agent searched the security skill for "formula injection" itself, before the hook
fired. The hook then named the file. The agent knew the rule, read it, and declined to apply it.
The two remaining failing runs (w19, w20) each built most of what their rules required and missed
one test.

**The same shape across every version.** On the three cases no arm ever moved (w03, w06, w18):

- in v7 and v8, all 12 library runs named the risk in their final message and handed it back;
- none of the 3 `bare` runs mentioned it.

So the library does carry these rules to the model, as questions for the user. A rule test scores
"flagged and handed back" the same as "never considered" (ROADMAP 73 (g)).

**What the named arm had that no shipped mechanism has.** v7's named arm put the files in the
prompt as "engineering guideline files. They apply to this task". That made the rules part of what
was asked. That arm built the CSV guard, the session lifetimes and the login-enumeration fix. In v9
the same files arrived from the library, and the agents treated them as advice beyond the spec:
the router's operating principle 2 tells them to stop and ask on security-relevant choices, and
principle 5 accepts "deliberately handled elsewhere … say so". The linked run in w18 cited the
routing guidance and treated rate limiting as "the transport's job", in a repository with no
transport layer. This is a reading of the transcripts, not a tested cause.

**The linked index.** Its only gains over v8 (w04, w07, w20) are in cases where the agent built the
rule. In w07 the linked run read `code-security/01` and added the guard; the code run read the same
file and handed it back. One sample per case cannot separate the arms on that.

## What this says

1. **(h) solves file choice.** Selecting by the code reached a cited file in 18/20 runs, up from
   11/20 for v8. The offline replay predicted 17/20.
2. **File choice was not the last constraint.** With the right file read in full, agents mostly
   name the rule and ask instead of building it. The next lever is the instruction's standing:
   whether a rule from the library counts as part of the task.
3. **A link in the first-depth index is followed sometimes.** With the table, 15/20 runs opened a
   cited file, against v8's 11/20 with the same hook. Rule tests rose +0.075 over v8 and +0.057
   over the control. Both are below the pre-registered bar.

## Limits

- n = 20 per arm, one sample per case, one model, Python only.
- **Reused controls**: v7's rows from about 9 hours earlier and v8's from about 2 hours earlier.
- The trigger table was written by someone who had read the 20 tasks (in-sample, as
  pre-registered). Its offline recall was 17/20; the measured reach was 18/20.
- "Handed back" is read from each run's final message. The table above quotes it, but it is not a
  scored measure, and nothing here tests that the framing causes the deferral.
- The code arm costs 58% more per run than the control, mostly in reading: 818 rules lines per run.

## Deviations

None.

## Spend

| reading | account usage | note |
|---|---|---|
| 2026-10-11 23:49 CEST | $919.9028 | settled, before v9 |
| 2026-10-12 00:06 CEST | $920.7871 | after the gates and pilot: +$0.88 |
| 2026-10-12 00:29 CEST | $939.1477 | +$18.36 since 00:06; **first reading, the counter lags** |

The SDK estimate is $22.16 for the 40 runs, plus $1.17 for gates and pilot ($0.23 preflight, $0.04
probe, $0.90 pilot). Credit left at 00:29: $10.85.

The transcripts and final workspaces stay in the git-ignored `results/v9-2026-10-12/`.
