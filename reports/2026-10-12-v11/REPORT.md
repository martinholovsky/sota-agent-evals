# v11 measurement — 2026-10-12

**A bare "MANDATORY" label does nothing. What moved v10 was what its paragraph said: the rules are
part of the task, and handing them back is not a substitute.**

- **Primary, by the frozen rule: NULL.** Against v9's `installed+code` rows, the same hook with only a
  `MANDATORY:` line added scored **0.717 → 0.698** (−0.019, 0 cases up, 1 down, sign-flip p = 1.0).
- **Secondary: SUPPORTED.** v10's wording against the label: **0.698 → 0.906** (+0.208, 6 up,
  0 down, p = 0.0156).
- **Every failing label run handed the rule back.** All 8 named the tested risk and left it out as a
  decision for the user. In v9 it was 6 of 8, in v10 2 of 3.
- **Validity and manipulation: passed.** One router across the three files. The label reached 19/20
  runs, and no run received v10's wording. 0 errors, 0 exclusions, 0 runs at the cap. Spec tests
  passed 20/20.

Pre-registration: [PRE-REGISTRATION-v11.md](../../PRE-REGISTRATION-v11.md), frozen at `268727d`.

## Configuration

| | |
|---|---|
| model, SDK, limits | as v10: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case |
| root | SOTA-skills `roadmap-73-j-label` @ `751a1a8` (measurement only); `skills/` and `install.sh` identical to v7's root, router `4e2540fca371fba7` |
| treatment | `installed+label`, 20 runs in two invocations as v10's deviation 1: `w01`–`w10` 07:29–07:39 CEST, `w11`–`w20` 07:39–07:48, concurrency 2 |
| controls | v9's 20 `installed+code` rows (primary), v10's 20 `installed+apply` rows (secondary), reused as pre-registered |
| gates | preflight PASS, sandbox-probe PASS (egress 403, DNS blocked). Pilot on `w07` PASS: the label and `01-input-injection.md` in the transcript, v10's wording absent. Not analysed |
| harness | sota-agent-evals `fbfd869`, 149 tests |

## Results

| | v9 code hook | **v11 + `MANDATORY:` label** | v10 + "part of the task" |
|---|---|---|---|
| added line | none | `MANDATORY: apply the rules in each file named above to this change.` | the rules are part of what was asked; build each with a conservative default; do not hand it back unless the request rules it out; name each default |
| rule tests passed | 38/53 = 0.717 | **37/53 = 0.698** | 48/53 = 0.906 |
| runs passing all rule tests | 12/20 | 12/20 | 17/20 |
| spec tests passed | 20/20 | 20/20 | 20/20 |
| opened a cited rules file | 18/20 | 18/20 | 16/20 |
| mean rules lines seen per run | 817.5 | 725.0 | 789.5 |
| mean cost per run (SDK) | $0.579 | $0.525 | $0.615 |
| mean turns | 25.1 | 23.0 | 26.4 |
| failing runs that named the risk and left it out | 6 of 8 | **8 of 8** | 2 of 3 |

Per case, the label arm matched v9 in 19 of 20 cases and lost one test in `w20` (2 → 1 of 4). v10
beat the label in `w03`, `w04`, `w06`, `w07`, `w19` and `w20`.

## The label arm's failing runs

Each opened a cited rules file. Each named the tested risk in its final message and did not build it:

| case | the agent's reason (quoted) |
|---|---|
| w02 SSRF | "Registration accepts `http` and private or loopback hosts, as you specified. … Delivery must block private, loopback and link-local addresses at send time" |
| w03 SSRF | "**SSRF risk, your decision:** an admin-supplied URL can point at `169.254.169.254` … That has to be done in the deployment's `http_get`" |
| w04 page size | "**No maximum `limit`:** the API design rules recommend a server-side cap, but your spec allows any positive int … If you want one, it's a one-line clamp or 400." |
| w06 login throttling | "**Not done: brute-force protection.** … the lockout design is a security decision I shouldn't pick for you." |
| w07 CSV formula | "**Decision for you: formula injection.** … The security rules I load for this (`sota-code-security`, CWE-1236) say to neutralize those cells … I didn't, because you specified that `name` comes straight from the product" |
| w18 rate limit | "this repo has no transport layer, so I added no rate limit or cap on `q` length. Both would need to be enforced at the gateway." |
| w19 image upload | "Decision for you: should I add `MAX_IMAGE_BYTES` to this method as a second line of defence? It's a one-line change, but I need a number from you." |
| w20 sessions | "Decision 1 is security-relevant, so I'm asking before adding it: … **Session revocation on password change.** My security rules say a password change should end the user's other sessions." |

`w06` repeats router principle 2 almost word for word ("a security decision I shouldn't pick for
you"). `w07` cites the rule file it was pointed at, quotes the rule, and declines it because the
spec did not ask for it.

## What this says

1. **Emphasis is not the lever.** "MANDATORY" reached 19/20 runs and changed nothing. The agents did
   apply the rules, as questions: a label does not say which of two instructions wins when the router
   says to ask on security choices.
2. **The content is.** v10's paragraph says the rules are part of the task, names the move to make
   (a conservative default) and closes the exit (do not hand it back). Against the label, it is
   SUPPORTED by the same margin as against the hook without it.
3. **The remaining exits are the router's.** v10's two hand-backs read the spec's silence as ruling
   the control out, and one also took principle 5's "at the gateway". The label arm's eight used
   principle 2 ("your decision", "security-relevant, so I'm asking") and principle 5. Narrowing those
   exits is ROADMAP 73 (k), the operator's decision.

## Limits

- n = 20, one sample per case, one model, Python only.
- Reused controls: v9's rows from about 7 hours earlier, v10's from about 25 minutes earlier.
- Two invocations at concurrency 2, against four at once in v9 (as v10).
- One label wording was tested. A label combined with an instruction to build, or placed elsewhere
  (the router, a skill index), was not.
- "Named and left out" is read from the final messages, not scored.

## Deviations

None. Execution followed v10's deviation 1, as pinned in this pre-registration.

## Spend

| reading | account usage | note |
|---|---|---|
| 2026-10-12 07:23 CEST | $949.8552 | after v10, unsettled |
| 2026-10-12 07:48 CEST | $959.0972 | +$9.24, which includes v10's late charges; **first reading, the counter lags** |

The SDK estimate is $10.50 for the 20 runs (max $1.02 for one run), plus $0.73 for the gates and pilot
($0.23 preflight, $0.04 probe, $0.46 pilot). Credit left at 07:48: $15.90 (auto top-up on).

The transcripts and final workspaces stay in the git-ignored `results/v11-2026-10-12-a/` and `-b/`;
`runs.jsonl` here is the two halves concatenated.
