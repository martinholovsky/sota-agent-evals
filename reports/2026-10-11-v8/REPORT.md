# v8 measurement — 2026-10-11

**Agents now read the rules files whole, but the wrong ones. Which file they read decides the
outcome.**

- **Primary, by the frozen rule: NULL.** With ROADMAP 73 (d'), the depth hook asks agents to choose
  one or two rules files and read each in full. Rule tests went **0.698 → 0.679** (−0.019, 0 cases
  up, 1 down, sign-flip p = 1.0), against v7's `installed` rows.
- **Validity and manipulation: passed.** One router across both files. 20/20 treatment rows have a
  transcript and received the hook's text; no control row did. 0 errors, 0 exclusions, 0 runs at
  the cap. Every run passed its spec tests.
- **The mechanism worked.** Mean rules lines seen per run rose from **78.7** (v7's hook) to
  **472.1**. That is at the level of v7's named arm (448.2). Rules text reached **20/20** runs.
  So agents did read in full, and the pre-registered "not followed" reading does not apply.
- **What failed is the choice of file.** A cited rules file was opened in **11/20** runs (v7's hook:
  12/20). 10 of the 20 runs never loaded `sota-code-security`, where 58 of the 74 citations sit:
  they followed the hook's one named action, "invoke the language skill", and read `sota-python`
  rules in full.

Pre-registration: [PRE-REGISTRATION-v8.md](../../PRE-REGISTRATION-v8.md), frozen at `e70b517`.

## Configuration

| | |
|---|---|
| model, SDK, limits | as v7: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, CLI `2.1.286`, 60 turns, $1.50, 1500 s, 1 sample per case |
| root | SOTA-skills `roadmap-73-d-full-read` @ `8c48945`; `skills/` and `install.sh` identical to v7's root |
| treatment | `installed+depth` with the (d') hook text, 20 runs, one invocation, 22:01–22:10 CEST |
| control | v7's 20 `installed` rows, reused as pre-registered |
| gates | preflight PASS, sandbox-probe PASS (egress 403, DNS blocked). Pilot on `w20` PASS: transcript present, hook text reached the model, and it contained the new "Read each of them in full". Not analysed |
| harness | sota-agent-evals `b96d263`, 138 tests. Replaying v7's depth rows through `--v8` reproduces v7's NULL (+0.019) |

## Results

| | v7 `installed` (control) | v7 depth hook | **v8 depth hook, full read** | v7 files named |
|---|---|---|---|---|
| rule tests passed | 37/53 = 0.698 | 38/53 = 0.717 | **36/53 = 0.679** | 46/53 = 0.868 |
| runs passing all rule tests | 12/20 | 13/20 | 11/20 | 16/20 |
| rules text in a tool result | 5/20 | 14/20 | **20/20** | 20/20 |
| mean rules lines seen per run | 26.8 | 78.7 | **472.1** | 448.2 |
| opened a cited rules file | 5/20 | 12/20 | 11/20 | 20/20 |
| mean cost per run (SDK) | $0.366 | $0.427 | $0.498 (+36%) | $0.442 |
| mean turns | 19.4 | 23.5 | 23.6 | 19.5 |

Only the v8 column is new. The other columns are v7's own rows, for comparison and not re-tested.

**The six cases the named arm improved,** and what v8's run read in full:

| case | control | v8 | named | v8 read | the cited file it did not read |
|---|---|---|---|---|---|
| w02 callback SSRF | 0/2 | 0/2 | 1/2 | `api-design/06`, `python/05` | `code-security/01` (SSRF) |
| w04 pagination | 1/2 | 1/2 | 2/2 | `api-design/01` | none: it read the cited file and did not gain |
| w06 login throttling | 0/3 | 0/3 | 1/3 | `code-security/02`, `/07` | none: it read the cited file and did not gain |
| w07 CSV formula | 0/2 | 0/2 | 2/2 | `python/05`, `python/07` | `code-security/01` (formula injection) |
| w19 image upload | 3/4 | 3/4 | 4/4 | `code-security/21` | `code-security/09` |
| w20 sessions | 1/4 | 1/4 | 4/4 | `code-security/17` | `code-security/02` (session lifetime) |

The one case that dropped, w08 (3 → 2), read `code-security/09` but not `code-security/01`. One
sample per case cannot separate that from run-to-run noise.

## What this says

1. **The hook can make agents read in full.** "Read each of them in full", stated as one concrete
   action, raised rules lines seen about six-fold. v7's NULL for the hook was partly a reading
   problem, and that part is now fixed.
2. **Reading in full does not help without the right file.** Agents chose files by the hook's other
   named action ("invoke the language skill") and by surface topic. For tasks whose risk the prompt
   never names (an SSRF in "fetch the callback URL", a formula injection in "export a CSV"), they
   did not reach the file that holds the rule. v7's named arm differed from v8 in **which files**
   were read, not in **how much**, and only the named arm moved outcomes.
3. **Choosing by the prompt's words fails too, and for the same reason.** Before v8, a BM25 match of
   each prompt against the rules index found a cited file for 6/20 cases (pre-registration). The
   signal that would select the right file is in what the agent **writes** (an outbound fetch of a
   caller-supplied URL, a CSV writer, a session token), not in what it is **asked**.
4. **Some rules do not land even when read.** In w06 the run read `code-security/02` in full and
   passed 0/3, and the named arm managed 1/3. As in v7, w03 and w18 failed in every arm. These are
   questions about those rules and tests, not about routing.

## Limits

- n = 20, one sample per case, one model, Python only.
- **The control is reused from v7**, measured 6 hours earlier. The `installed` arm scored 37/53 on
  two separate days, but drift on the provider's side would read as an effect here.
- "Opened a cited file" counts tool inputs naming the file (`Read`, `Bash`, `Grep`), not the lines
  read from it.
- The per-case attributions above are descriptive, not tested.

## Deviations

None.

## Spend

| reading | account usage | note |
|---|---|---|
| 2026-10-11 16:06 CEST | $910.7943 | v7's first reading; v7's counter had not settled |
| 2026-10-11 22:10 CEST | $919.8501 | +$9.06 since, which includes v7's late charges and all of v8 |
| 2026-10-11 23:49 CEST | $919.9028 | settled: +$0.05 since 22:10 |

The SDK estimate for v8 is $9.96 for the 20 runs, plus about $0.83 for gates and pilot ($0.23
preflight, $0.04 probe, $0.56 pilot). The account cannot separate v8 from v7's lagging charges.
Together, v7 and v8 settled at **$33.00** (14:38 → 23:49), against $39.87 estimated by the SDK, so
the account charged about 83% of the SDK estimate.
