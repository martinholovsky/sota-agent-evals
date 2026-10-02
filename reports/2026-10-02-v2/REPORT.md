# 2026-10-02 — v2 agent-loop measurement (Sonnet 5.5): clean run, no detectable effect, still near-saturated

**Verdict: H1, H2, H3 all NOT SUPPORTED, and the run cannot distinguish "no effect" from "no
room for an effect"** — the cases are still almost always solved in every arm. The one effect
that is clear is *behavioural*, not an outcome: the hook makes the agent verify unpiped (0% → 100%).

| | |
|---|---|
| pre-registration | [PRE-REGISTRATION-v2.md](../../PRE-REGISTRATION-v2.md), frozen before any v2 run |
| model | `anthropic/claude-sonnet-5.5` via OpenRouter |
| runs | 240 / 240 (20 cases × 4 arms × 3 samples) — **0 errors, 0 exclusions** |
| spend | **$26.60** (OpenRouter delta = SDK estimate); v2 total incl. pilot ≈ $28.0 |
| treatment checks | library arms list the skills, bare/hook uncontaminated, hook ledger in exactly the hook arms — all 240 |

## Pre-registered analysis (all 20 cases)

| arm | hidden_pass | shipped_broken | unverified_done |
|---|---|---|---|
| bare | 0.917 | 0.083 | 1.00 |
| library | 0.917 | 0.083 | 1.00 |
| hook | 0.950 | 0.050 | 0.00 |
| library+hook | 0.917 | 0.083 | 0.00 |

| hypothesis | diff | 95% CI | verdict |
|---|---|---|---|
| H1a hook vs bare — fewer broken "done" | −0.033 | [−0.083, 0.000] | NOT SUPPORTED |
| H1b library+hook vs library | 0.000 | [0.000, 0.000] | NOT SUPPORTED |
| H2 library vs bare — hidden_pass | 0.000 | [−0.050, 0.050] | NOT SUPPORTED |
| H3 hook vs bare — hidden_pass | +0.033 | [0.000, 0.083] | NOT SUPPORTED |

## Two of my cases were defective (found after the run; recorded as a deviation)

Only three cases ever failed. Inspecting each failure against its written spec:

- **d08 — defective.** The spec says long-word chunks go "each on its own line"; all 12 agents
  did exactly that. My reference let the last chunk share a line with the next word, and the
  hidden test encoded *my* reading. 12/12 failures across every arm: the case, not the agents.
- **d15 — defective.** The spec says the continuation backslash is "dropped" and the next line
  "appended with one space"; read literally, the space before the backslash survives
  (`one  two`). My reference also stripped it, which the spec never says. Agents split 7–5
  between the readings — the signature of an ambiguous spec.
- **d13 — a fair miss** (1/12, bare): "takes 50% … rounded DOWN" rounds the *discount*; the agent
  rounded the result (500 vs 501).

My pre-run review checked every hidden assertion against its spec and still missed both; the
tell afterwards was failures that were **identical across arms** (d08) or **split between two
readings** (d15). Neither is a selection-by-outcome edit: the case set is unchanged, the
pre-registered numbers above stand, and the analysis below is labelled post-hoc.

## Post-hoc sensitivity: without d08 and d15 (18 cases)

| arm | hidden_pass | shipped_broken |
|---|---|---|
| bare | 0.981 | 0.019 |
| library | 1.000 | 0.000 |
| hook | 1.000 | 0.000 |
| library+hook | 1.000 | 0.000 |

All four hypotheses remain NOT SUPPORTED (largest diff 0.019, CI touching 0). With the defects
removed **the set is saturated**: one genuine miss in 216 runs. Per the pre-registration this is
uninformative about H1–H3 — it says these tasks are within this model's reach in every arm.

## What does stand

- **Behaviour, both runs:** without the hook the agent never ran the test suite unpiped after its
  last edit (v1: 0/54 valid runs; v2: 0/120); with it, always (v1 49/49, v2 120/120). Loading
  SOTA-skills, whose rules say exactly this, did not change it.
- **No measurable outcome cost or benefit** from the library or the hook on these tasks with this
  model. "No benefit" is bounded by the ceiling, not demonstrated.

## What would make the next run informative

1. **Harder cases or a weaker model.** Self-contained spec tasks are at Sonnet 5.5's ceiling. A
   cheaper, weaker model (e.g. Claude Haiku 4.5) leaves room for both effects; so would
   multi-file tasks inside a real repository, where reading and verifying matter more.
2. **Every case independently spec-reviewed** — by a second reader who has *not* seen the
   reference — before freezing, since my own review missed two.
3. Budget: this session's spend is ≈ $42 of the $50 cap, so a third run needs a new budget.
