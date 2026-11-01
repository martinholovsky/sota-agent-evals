# v17: narrowing the router's exits (ROADMAP 73 (k)), same-day A/B. FROZEN 2026-11-01, before any v17 run

Status: **FROZEN 2026-11-01**, approved by the operator together with SOTA-skills #670's wording and
the run itself, before any v17 run or API spend.

## Question

The (l) rescoring ([report](reports/2026-11-01-l-handback/REPORT.md)) found that with the library
loaded, 131 of 145 failed rule tests had been **named and handed back**, not missed. The router's
principle 2 (stop-and-ask on security decisions) and principle 5 ("if one is handled elsewhere, say
so") are the exits those hand-backs use. SOTA-skills draft PR #670 narrows both: build a
conservative default where one exists and the request does not rule it out, and count a control as
handled elsewhere only when the agent can name where. **Does that raise the rule-test pass rate,
without lowering the spec pass rate?**

## Arms (same day, same model, same cases, interleaved runs)

| arm | `--arms` | SOTA-skills root | root digest (`--expect-root-digest`) |
|---|---|---|---|
| control | `installed+table+code` (the shipped default, as v14 and v16) | `main` at `3cffee72` | `7db7bbdda73b9a06` |
| treatment | `installed+table+code` | `roadmap-73-k-router-exits` at `62087351` (#670) | `ad0c58d7ec049098` |

`git diff --stat 3cffee72 62087351 -- skills commands hooks scripts/code-rules-hook.py` is one file,
`skills/sota/SKILL.md`, 6 lines changed: the router is the only loaded difference. The two arms are
two invocations (one per root), started together.

## Cases

`cases-v5`, a fixed 12-case subset drawn before any run by
`sorted(random.Random(17).sample(sorted(ids), 12))` over the 20 ids:
**w02, w03, w05, w09, w10, w12, w13, w14, w17, w18, w19, w20** (20 rule tests per arm). The rule
was fixed without reference to any model's results on these cases. One sample per case per arm.

## Model, provider, limits

- `--provider anthropic`, `--model claude-sonnet-5-5` (Anthropic API, not OpenRouter: the operator's
  decision 2026-10-31). The key is read from SOTA-skills' git-ignored `.env`, exporting only
  `ANTHROPIC_API_KEY`, never echoed; the runner removes secret-named variables from the agent's
  environment as before.
- `claude-agent-sdk` as pinned in `uv.lock`; `--max-turns 60`; `--max-budget-usd 1.50` per run;
  `--concurrency 2` per invocation.
- **The provider changed since v16**, so no comparison to any earlier version is made.

## Outcomes and decision rule

- **Primary: rule-test pass rate** per arm (rule tests passed / 20). **SUPPORTED** if treatment −
  control ≥ +0.20 **and** one-sided Fisher exact p < 0.05; **NULL** if treatment − control ≤ +0.05;
  otherwise **INCONCLUSIVE**.
- **Harm guard (overrides SUPPORTED):** if the treatment's spec pass count is lower than control's by
  more than 1 case, the result is **HARM**, whatever the primary.
- **Secondary (descriptive):** each failed rule test labelled HANDED_BACK / CLAIMED_DONE /
  NOT_CONSIDERED with the (l) rubric and judge, validated as in (l); cost per run (SDK estimate);
  turns; how many runs name a chosen default in their final message.

## What can be detected, stated now

Control is expected near 14/20 (the same arm scored 12/20 in v14 and 14/20 in v16 on this subset,
on another provider). Against 14/20, one-sided Fisher p is 0.118 for 18/20, **0.046 for 19/20**,
0.010 for 20/20. **Only a near-ceiling treatment can reach SUPPORTED**; a real but smaller gain reads
INCONCLUSIVE. n = 12 cases, one sample each, one model, one day.

## Prediction (recorded before any run)

Treatment 17–19/20, control 13–15/20 — most likely INCONCLUSIVE at this size; the secondary should
show fewer HANDED_BACK failures in the treatment arm.

## Gates (any failure stops v17)

As v16: preflight on each root (the arm resolves, the router and hook reach the model, the row
carries the root digest), then a one-run pilot per arm; both must pass before the 24 runs.

## Budget (operator cap $25, gates + pilot + run)

Expected, at v16's cost per run (about $0.57; the provider change may move it):
- gates about $0.6 (two roots);
- pilot about $1.2 (one run per arm);
- run about $13.7 (24 runs).

That is about $15.5. Worst case, from what the runner actually enforces:
- **gates and pilot: a hard stop at $2.50** for the two together (expected about $1.8): if they cost
  more, v17 stops before the run and returns to the operator;
- **run:** `--total-budget-usd 8` per invocation. The guard checks the summed SDK estimate before
  starting each run, so an invocation starts no run once it has spent $8, and at most 2 runs
  (`--concurrency 2`) × $1.50 (`--max-budget-usd`) are in flight when it trips: at most $11 per
  invocation, $22 for both.

Worst case total: $2.50 + $22 = **$24.50**, under the $25 cap. The guard counts the SDK's per-run
cost estimate; the Anthropic provider gives this runner no external usage counter, so the spend of
record is the SDK estimate, read again from the Anthropic console by the operator after the run.

## Deviations

(None yet.)
