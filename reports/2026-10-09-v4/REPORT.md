# v4 measurement — 2026-10-09

**The routing layer works; the routing chain mostly stops at the router.**
- **Manipulation check, primary: PASSED.** **20/20** `installed` runs invoked a SOTA skill,
  against 0/166 library runs without the routing layer in v1–v3. The same model was used.
- **H4** (`installed` vs `bare`, hidden_pass): **NOT SUPPORTED** (diff 0.0, CI [0, 0], n = 20)
  and **uninformative** by the ceiling rule, with 1.00 in both arms.
- **Routing depth, descriptive, decided before measurement:**
  - **20/20** runs invoked the router;
  - **1/20** invoked a further skill through the `Skill` tool;
  - **3/20** went past the router in any way (two by `Read` of a `SKILL.md`);
  - **0/20** read a rules file.

Pre-registration: [PRE-REGISTRATION-v4.md](../../PRE-REGISTRATION-v4.md). Its "Deviations" section
records every decision taken before measurement: the model, arms and pin, the chunking, and the
402 re-run rule.

## Configuration

| | |
|---|---|
| model | `anthropic/claude-sonnet-5.5` via OpenRouter |
| arms | `bare`, `installed` (skills + `UserPromptSubmit` hook + `CLAUDE.md` directive produced by the pinned `install.sh`'s own `emit_routing_block` + `skillListingBudgetFraction` 0.07) |
| SOTA-skills pin | `main` @ `1d19530` (includes #517: router BUILD step 4 lists step 2's files and fails on an empty list) |
| per-run limits | 60 turns, $1.50, 1500 s; concurrency 4 |
| gates, immediately before | preflight PASS ($0.23); sandbox-probe PASS (key vars 0, egress 403, DNS blocked) |
| harness | `claude-agent-sdk==0.2.163`, CLI `2.1.286`, 79/79 tests |
| analysis | `python -m agent_evals.analyze --v4 runs.jsonl` → `analysis-preregistered.json` |

## Rows

There are 46 rows: 40 valid, one per case × arm, with all 20 cases covered in both arms. **6 rows
errored** in chunk 2a with OpenRouter `402 … would exceed your available credits given your current
in-flight requests`: t12 installed, t13 bare, t14 and t15 in both arms. OpenRouter reserves credit
per in-flight request, and with 4 concurrent sessions the reservations exceeded a ~$5 balance
before the $2 auto top-up could fire. These are infrastructure failures. Under the rule recorded
before any re-run, the six jobs were re-run unchanged once credit allowed; all six re-runs are
valid. The errored rows are kept here and counted (`excluded: error:bare 3, error:installed 3`).

**The 10% rule, read literally**, says ">10% excluded in any arm → compromised". With the errored
originals counted that is 3/23 ≈ 13% per arm, so the literal rule flags it. **Read as intended**,
it says the measurement is complete: every planned job has exactly one valid row, and no case is
missing from either arm. Both readings are given; neither is hidden.

## Results

| arm | hidden_pass | unverified_done | shipped_broken | runs invoking a skill |
|---|---|---|---|---|
| bare | 1.00 | 1.00 | 0.00 | 0/20 |
| installed | 1.00 | 1.00 | 0.00 | **20/20** |

**Depth (installed, 20 valid runs):**
- **Skills invoked:** `sota` 20, `sota-code-security` 1, `sota-testing` 1 (t16).
- **Past the router by `Read`:** t13 read `sota-python/SKILL.md`; t18 read `sota-python/SKILL.md`
  and `sota-testing/SKILL.md`.
- **No run read any `rules/` file**, which is where the audit checklists live.

The pilot on the pre-#517 router (2026-10-09, 3 runs) went past the router in 0/3. 3/20 here is
consistent with a small effect of #517, and equally with none; n is too small to tell.

## What this means

1. **The routing layer is what makes the library get used.** Sonnet-5.5 invoked it 0/166 times
   without the routing layer and 20/20 with it.
2. **These tasks cannot show whether the rules help.** Both arms pass every hidden test. v1, v2
   and v3 all saturated, and so does v4. A task set with headroom for this model, or a
   rules-specific scorer (did the change meet the applicable checklist items?), is what would.
3. **The router's own instruction, "load the matching `sota-*` skills", is followed in a minority
   of runs, and the rules files are never reached.** This is now the limiting step: the library
   reaches the model as a router and almost never as rules.

## Spend

- **SDK estimate for the 40 + 6 jobs:** $13.87.
- **Account figure:** pending. OpenRouter's usage counter lags by hours (v3's first reading was
  off by about $11, see the v3 report), so the settled account figure will be added after it
  settles, with two readings.

## Limits

- One model, one Python application, S = 1.
- Ceiling on hidden_pass.
- Routing depth is counted from tool calls: a rules file the model saw by other means would not
  count, and there was no such evidence in any trace.
