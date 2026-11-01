# v17: narrowing the router's exits (ROADMAP 73 (k)) — NULL, 2026-11-01

[Pre-registration](../../PRE-REGISTRATION-v17.md), frozen before any run. Same-day A/B on the
Anthropic API (`claude-sonnet-5-5`), arm `installed+table+code`, 12 seeded `cases-v5` cases.
Control: SOTA-skills `main` at `3cffee72` (root `7db7bbdd`). Treatment: SOTA-skills #670 at
`62087351` (root `ad0c58d7`), whose only loaded difference is the router's principles 2 and 5.

## Result

| | control | treatment |
|---|---|---|
| rule tests passed | 12/20 | 12/20 |
| spec passed | 12/12 | 12/12 |
| cases up / down (treatment vs control) | — | 0 / 0 |
| router table reached the model | 12/12 | 12/12 |
| hook spoke | 6/12 | 6/12 |
| mean turns | 12.8 | 12.2 |
| failed rule tests: handed back / claimed done / not considered | 7 / 1 / 0 | 7 / 1 / 0 |
| cost (SDK estimate) | $3.56 | $3.48 |

**Decision rule: NULL** (difference 0.00, threshold for NULL ≤ +0.05). No HARM (spec equal). The
treatment reached the agents (a different router hash in every treatment row; the table in 12/12),
and the twelve cases scored identically in both arms: w02, w05, w09, w12, w14, w17 and w18 pass
their rule tests in both; w03, w10, w13, w19 and w20 fail all of theirs in both.

## Why, from the final messages

The narrowed wording still lets the agent decline when "the request rules it out", and the
treatment agents used exactly that exit, reading the user's specification as ruling the control
out: "your spec says every use extends the session" (no absolute lifetime), "a cap would return
fewer orders than you asked for, which contradicts 'pages of `page_size`'", "your spec lists no
429 status" (no rate limit). Control agents deferred the same controls with "since you gave none"
and "the spec only asks for one on creation". The exit moved from "handled elsewhere" to "the spec
rules it out"; the behaviour did not change. In w13 both arms judged plain SHA-256 adequate for
high-entropy recovery codes — a disagreement with the rule, not a hand-back.

## Limits

12 cases, one sample each, one model, one day; the design could only reach SUPPORTED near the
ceiling (19/20 or 20/20 against control's 12/20 would have been needed), but an exact case-by-case
tie leaves no gain to detect.

## Files

`control-runs.jsonl`, `treatment-runs.jsonl` (the runner's rows), `failure-labels.jsonl` (human
and judge labels for the 16 failed rule tests, 16/16 agreement). Raw transcripts stay in the
gitignored `results/`.
