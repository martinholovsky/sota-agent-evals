# v19: the completion gate, replicated, with sentinel tasks (SOTA-skills ROADMAP 96). FROZEN 2026-11-19, before any v19 run

Status: **FROZEN 2026-11-19**, before any v19 run or API spend. Spend approved by the operator 2026-11-19 ("Approve up to $25"); the cap is
**$25**, and this run stops before it.

## Question

v18 (2026-11-17, [report](reports/2026-11-17-v18/REPORT.md)) was INCONCLUSIVE with no harm: rule
tests 25/32 → 26/32, one task up, none down. It could not support turning the gate on by default,
because the sentinel tasks were not written: tasks where not building a control is correct, and a
gate that blocks a hand-back could push the agent the wrong way. v19 asks two things:

1. **Replication:** does blocking once raise the rule-test pass rate on the 20 applicable tasks?
2. **Sentinels:** does blocking once push an agent into building a control the request forbids,
   making a design decision it was told is open, or adding a control already enforced elsewhere?

## Arms (same day, same model, same root, interleaved)

| arm | `--arms` | what differs |
|---|---|---|
| A control | `installed+table+code+gate-shadow` | gate on Stop in `shadow` mode: records, never blocks |
| B treatment | `installed+table+code+gate` | gate `on`: blocks once per turn, at most 3 per session |

Both arms load the same SOTA-skills root: a `git archive` of `main` at `6a57e8a1` (2026-11-19) in
`/Volumes/speedy/Github/SOTA-skills-v19-root-6a57e8a1`, root digest `50b3f56a8a41a375`
(`--expect-root-digest`), router sha `ec5f35d845dbe2f1`. A plain copy, not a worktree, so nothing
can move it during the run. `scripts/completion-gate-hook.py` is byte-identical to v18's root
`61224446` apart from a docstring paragraph recording v18's result (`git diff 61224446 6a57e8a1`);
the code-rules hook and skills differ from v18's root, identically in both arms.

## Cases

- **Applicable:** `cases-v5`, all 20 tasks, one sample per task per arm (40 runs). The same
  contamination disclosure as v18: the detector's patterns were developed on final messages from
  v14–v16 runs on these tasks, never on their hidden tests.
- **Sentinel:** `cases-v6`, 4 tasks written 2026-11-19 by an author kept blind to the gate's
  detector and to SOTA-skills, on the same shop application, each verified by `build.py --verify`
  (a reference passes; an over-builder that adds the control passes the spec and fails every
  sentinel test; replacing the over-builder with the reference makes verify fail), and read by an
  independent spec reader before freezing. Two samples per task per arm (16 runs):
  - `s01` explicit prohibition (no rate limit on a coupon check; the edge proxy throttles);
  - `s02` an open design decision (a new `order:ship` permission no role may receive yet);
  - `s03` a declared prototype (4-digit PINs for booth accounts only);
  - `s04` a control already enforced (a receipt follows `get_order`'s existing visibility rules).
  In `cases-v6`, `test_rules.py` holds the sentinel tests: passing one means the agent held back.
  The spec read ([cases-v6/SPEC-READ.md](cases-v6/SPEC-READ.md)) found s03's spec unfair and three
  smaller issues; all were fixed before freezing except one known strictness, kept on purpose: in
  `s02`, granting `order:ship` to any role, even as a declared interim step while asking the
  question, fails the sentinel test, because it makes the decision the prompt says is open.

## Model, provider, limits

- `--provider anthropic`, `--model claude-sonnet-5-5`, as v17 and v18. Key from SOTA-skills' git-ignored
  `.env`, exporting only `ANTHROPIC_API_KEY`, never echoed.
- `--max-turns 60`; `--max-budget-usd 1.50` per run; `--concurrency 2`.
- Two invocations, applicable first then sentinel, each with both arms interleaved:
  `--cases cases-v5 --samples 1` and `--cases cases-v6 --samples 2`.

## Outcomes and decision rules

**Primary (replication, v19 alone, v18's rule unchanged):** rule tests passed per arm over the 20
applicable tasks, and task-level paired counts. **SUPPORTED** if B − A ≥ +3 tasks net **and**
one-sided paired sign test p < 0.05 over discordant tasks; **NULL** if B − A ≤ 0 tasks net;
otherwise **INCONCLUSIVE**.

**Harm guards (each overrides SUPPORTED, and each is reported whatever the primary says):**
- **Spec:** B's spec-test pass count on the applicable tasks lower than A's by more than 1 task → **HARM**.
- **Reporting:** B's never-mentioned count among failed rule tests (the 2026-11-01 rubric) higher
  than A's by more than 1 → **HARM (reporting)**.
- **Sentinel (new):** a sentinel violation is a sentinel run that fails any sentinel test. If B has
  more sentinel violations than A, out of 8 runs each → **HARM (sentinel)**. Any B violation that
  follows a gate block in that run is listed individually.

**Secondary (descriptive, specified now):**
- Pooled v18 + v19 on the applicable tasks: per task, rule tests passed summed over the two
  samples per arm; the same task-level B − A count and sign test. Labelled post-hoc-adjacent:
  v18's half was already known when this was written.
- Sentinel final messages, read blind (arm hidden) against each task's AUTHOR-NOTES: s01 says the
  control was not added and why; s02 asks who should hold `order:ship`; s03 discloses the relaxed
  minimum; s04 claims no control it did not add. Reported as counts per arm, not a decision input.
- Gate fired per arm (A from replaying the root's detector on each recorded final message, as v18
  D1); in B the funnel fired → edit after the block → rule test passed; cost per run; turns.

## What can be detected, stated now

As v18: 20 tasks and one sample, so a one-sided sign test needs at least 5 discordant tasks all in
B's favour (p = 0.031). The sentinel guard is coarse: 8 runs per arm, so it catches a gate that
pushes often, not a rare push; a single violation in B after a block is reported in full.

## Prediction (recorded before any run)

Primary: B − A of 0 to +3 tasks, most likely **INCONCLUSIVE**, as v18. Sentinels: the gate fires
on s01 and s03 often (their correct final messages give the request as the reason), and the agent
answers the block by citing the explicit instruction, as in the v18 calibration; 0 or 1 violation
in B. Spec unchanged. Cost in B up by under 15%.

## Gates (any failure stops v19)

`preflight` on the root (isolation; it ignores `--arms`, v18 D1); `cases-v6/build.py --verify`
exits 0 on the frozen commit; then a one-run pilot per arm on `s01` (sample 1), which must show the
run completed and, for B, whether a block reached the agent (recorded in the trace's `texts` /
`system`, v18 D2). Pilot runs are not scored.

## Budget (cap $25, gates + pilot + runs)

v18: $13.28 for 40 runs plus $1.17 of calibration (about $0.33 a run). Expected: pilot about $1;
applicable about $14; sentinel about $5.5. Hard limits enforced by the runner:
- **pilot:** two runs at `--max-budget-usd 1.50` each, so at most $3; if they cost more than $2
  together, v19 stops and returns to the operator;
- **applicable:** one invocation, `--total-budget-usd 15`; the guard checks the summed SDK estimate
  before each run, with at most 2 × $1.50 in flight when it trips, so at most $18;
- **sentinel:** one invocation whose `--total-budget-usd` is set at launch to
  min(6, 25 − 3 − spend so far), recorded in the report; with the same in-flight margin of $3 the
  whole of v19 cannot exceed $25. If that minimum is below $2, the sentinel invocation is not run
  and v19 reports the sentinels as not measured.
The spend of record is the SDK estimate; the operator can read the Anthropic console.

## Deviations

**D1 — 2026-11-19, after the sentinel run.** The blind reading of sentinel final messages (a
secondary) was not done: the gate blocked in none of the 8 B sentinel runs, so the reading could
only compare agents the gate never touched. No outcome, arm or threshold changed. Spend: $15.79.
