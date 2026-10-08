# v3 measurement — 2026-10-08

**Verdict: every hypothesis NOT SUPPORTED, and every comparison is UNINFORMATIVE by the frozen
ceiling rule.** A second finding outweighs the verdict: **the library arms never used the
library.** In all 40 library-arm runs, and in every library-arm run since v2 (166 of 166), the
agent invoked **zero** SOTA skills.

Pre-registration: [PRE-REGISTRATION-v3.md](../../PRE-REGISTRATION-v3.md), frozen 2026-10-03. The
operator's B ($20.00, so S = 1) was committed in `4d47f6b` before any measurement spend.
Deviations: none.

## Run

| | |
|---|---|
| command | `python -m agent_evals run --sota-root <SOTA-skills @ 9c00cc8> --cases cases-v3 --provider openrouter --model anthropic/claude-sonnet-5.5 --arms bare,library,hook,library+hook --samples 1 --max-turns 60 --max-budget-usd 1.50 --timeout 1500 --concurrency 4 --total-budget-usd 20` |
| gates, immediately before | preflight PASS ($0.228); sandbox-probe PASS: key vars 0, egress 403, DNS blocked |
| harness | `claude-agent-sdk==0.2.163`, bundled CLI `2.1.286` (same as the pilot); 75/75 harness tests |
| rows | 80 / 80, 0 errors, 0 excluded, 0 contaminated |
| analysis | `python -m agent_evals.analyze --v2 runs.jsonl` → `analysis-preregistered.json` |

## Pre-registered result

| arm | hidden_pass | unverified_done | shipped_broken |
|---|---|---|---|
| bare | 1.00 | 1.00 | 0.00 |
| library | 1.00 | 1.00 | 0.00 |
| hook | 1.00 | 0.00 | 0.00 |
| library+hook | 1.00 | 0.00 | 0.00 |

H1a, H1b, H2 and H3 are all NOT SUPPORTED, with diff 0.0 and CI [0, 0] over 20 paired cases. The
**ceiling rule** applies to every hidden_pass comparison: both arms reach 1.00, so each is
uninformative whatever its verdict line says. H1 is uninformative too, because no arm shipped
anything broken, so there was nothing for the hook to reduce.

**Is the 1.00 real or a broken scorer?** It is real. `cases-v3/build.py --verify`, re-run
2026-10-08, reports 0 of 20 tasks with problems: each task's starting repo FAILS its hidden
tests, and its reference solution passes. The same container scorer returned `hidden=False` for
both of today's preflight runs. `claude-sonnet-5.5` solved all 20 change tasks in every arm.
They were designed to be harder than v2, and v3 is the third case set this model class has
saturated.

**Descriptive only (pre-registered as such):** unverified_done is 1.00 without the hook and
0.00 with it. The hook does what it says: no hooked run ended without a passing, unpiped test
after its last edit. On these tasks that discipline changed no outcome, because the unhooked
runs' code passed anyway.

## The library arm did not test the library

| source | library-arm runs | runs with ≥ 1 Skill call |
|---|---|---|
| v2 (2026-10-02) | 120 | **0** |
| v3 pilot (2026-10-03) | 6 | **0** |
| v3 (this run) | 40 | **0** |

The skills were installed and listed: `treatment_present: true, listed: 42` in every library
run. But the model never called the `Skill` tool, and no trace reads a skills path. That was
checked two ways: the harness counter (`score.contamination`), and a raw scan of all 80 traces
with a positive control (`Bash` found in 80/80, `Read` in 52, SOTA names in the init listing of
exactly the 40 library traces).

So every "library vs bare" verdict this repo has published measured **skill descriptions
present in the listing**, not rules applied. The cause is the arm design, not the library.
Each run is isolated to a fresh config directory, so the library arm gets the skills **without**
the always-on routing layer SOTA-skills' installer adds: the `UserPromptSubmit` hook and the
global directive. The library ships that layer precisely because skills alone do not activate
reliably. **The next run must add an arm that installs the library as `install.sh` does**,
skills plus routing hook plus directive. It should also report skill-call counts as a primary
manipulation check, not leave them inside a contamination field.

## Spend

**Corrected 2026-10-08, the same evening. The first version of this section was wrong.** It said
the account had moved only $4.03, the run cost "~$3.77", and the SDK over-estimated by "~4.8×".
That reading was taken right after the run, and **OpenRouter's usage counter lags**. Re-read
about an hour later, with only ~$0.19 of probes spent in between, the account showed
**$12.8952** used since before the preflight. Taking out the preflight ($0.2280), the sandbox
probe ($0.0392) and two listing probes ($0.1888) leaves **≈ $12.44 for the 80-run measurement**,
or about $0.155 per run. The day's key `usage_daily` (`$18.98` = the same day's $6.08
SOTA-skills placebo + $12.90) reconciles with it.

- **SDK estimate:** $18.0902, so it ran **≈ 1.45× high** on this run. The v3 pilot found it 16%
  low; the direction is not stable, and the mechanism is unverified.
- **Labelling defect:** the runner prints the larger of its two meters under the label
  "OpenRouter spend". Here that was the SDK estimate.
- **The lesson for every report here:** read the account after the counter settles, and take two
  readings, never one taken immediately after the run.

## Limits

- S = 1: one run per case × arm.
- One model, `claude-sonnet-5.5`.
- One application, Python.
- SOTA-skills pinned at `9c00cc8` (2026-10-02, before `sota-swift`).
