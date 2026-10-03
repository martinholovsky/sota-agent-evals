# 2026-10-02 — first agent-loop measurement: COMPROMISED by a credit outage, and saturated

**Verdict: not a valid measurement of the pre-registered hypotheses.** Recorded in full because
a failed run is still evidence about the instrument, and two of its findings stand on the valid
rows regardless.

| | |
|---|---|
| model | `anthropic/claude-sonnet-5.5` via OpenRouter |
| runs | 240 (20 cases × 4 arms × 3 samples), concurrency 4 |
| spend | **$12.42** (OpenRouter delta = SDK estimate to the cent); 2026-10-04: did not hold for the v3 pilot (OpenRouter $2.70 vs SDK $2.27) — OpenRouter is the record |
| errored | **137 / 240** — every one OpenRouter `402`: *"would exceed your available credits"* |
| valid | 103: bare 30, library 24, hook 26, library+hook 23 |
| preflight | PASS immediately before; pilot treatment checks all correct |

## What went wrong

1. **The account ran out of credit, not the cap.** The $50 cap was per-key spend; the account
   behind the key had $2.47 left (other keys draw on the same credit). 57% of runs got a 402.
   The pre-registration excludes errored rows, but the exclusions are unbalanced across cases and
   arms, so the paired analysis rests on whichever samples happened to finish. **Fixed:** the
   runner now refuses to start unless the account's remaining credit covers `--total-budget-usd`.
2. **`hidden_pass` is saturated.** Every arm scored 0.95–1.00. A measure at the ceiling says the
   cases are too easy for this model, not that the library has no effect (SOTA-skills
   `sota-llm-engineering` rules/01 §8.1). H2 and H3 cannot be read from this run.

## What the valid rows do show

Pre-registered analysis (`analysis.json`, `python -m agent_evals.analyze runs.jsonl`):

| arm | hidden_pass | unverified_done |
|---|---|---|
| bare | 0.95 | 1.00 |
| library | 1.00 | 1.00 |
| hook | 0.95 | 0.00 |
| library+hook | 1.00 | 0.00 |

**Read H1 with this caveat:** the hook blocks until a test command runs unpiped, and
`unverified_done` checks for exactly that, so 0.00 in the hook arms is close to true **by
construction**. It shows the enforcement engaged in **49 of 49** valid hook runs. It does **not**
show better outcomes — that needs cases where the agent can fail.

**The behaviour it exposes, which does stand:** without the hook, on these tasks, Sonnet 5.5
in Claude Code

| | bare (n=30) | library (n=24) |
|---|---|---|
| ran no test command at all | 19 | 15 |
| ran tests **only** through a pipe (`… 2>&1 \| tail -5`) | 11 | 9 |
| ran an unpiped test after its last edit | **0** | **0** |

Spot-checked: the "no test" runs used no Bash or an ad-hoc `python3 -c` smoke check — never the
suite. The piped form reports `tail`'s exit status, so the agent read the text but the run
carried no machine-checkable result. Loading SOTA-skills (whose rules say exactly this:
`sota-shell-scripting` rules/01 §3, router principle 6) did not change it.

## Next run (needs a new pre-registration, not an edit of this one)

- Top up the OpenRouter account; the runner now checks it.
- A harder case set, so `hidden_pass` can move. Building it because *this* set saturated is a
  judgement about the instrument, recorded here, not selection by outcome of individual cases.
- An outcome metric for the hook that is not its own trigger: among runs whose hidden tests
  FAIL, how often did the agent end claiming success?
