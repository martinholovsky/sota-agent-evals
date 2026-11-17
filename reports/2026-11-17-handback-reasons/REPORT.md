# Why agents hand a control back: half of them read the request as excluding it — 2026-11-17

**Exploratory, retrospective, zero API spend.** It extends the 2026-11-01 rescoring
([`../2026-11-01-l-handback/REPORT.md`](../2026-11-01-l-handback/REPORT.md)), which found that with
the library a failed rule test is usually named and handed back (131 of 145), not missed. This
asks the next question: what reason does the final message give for not building it? The answer
decides what to try next. Protocol, categories and the decision rule were committed before any
labelling ([`PROTOCOL.md`](PROTOCOL.md), commit `a3a7dbd`); one amendment, made during author
labelling and before any judge ran, is recorded there with its timing.

## Population

The 138 items the 2026-11-01 instrument labelled HANDED_BACK (131 library arms, v7–v16; 7 `bare`,
v7), rebuilt with `tools/handback_items.py` (162 items, identical identity row by row to
`labels.jsonl`).

## Instrument, and its validation

1. **Author labels** on a seeded sample of 30 (`random.seed(17)`, [`sample_ids.json`](sample_ids.json)),
   by the session's model (Claude) — **not a human**. [`author-labels.json`](author-labels.json).
2. **Four blind judge subagents** (Claude, zero API spend), one per quarter, each seeing only id,
   test, risk, final text and the rubric; each label carries a deciding quote.
3. **Checks.** Every quote is a verbatim substring of its final text (138/138). Agreement with the
   author sample **29/30**; the one disagreement (item 34) is CANNOT vs ELSEWHERE on "…all have to
   live in the deployment's `http_get`. The catalog can't enforce them" — the two categories the
   rubric separates least well. Consistency: of 87 groups sharing a final text and risk, 1 got two
   labels (ELSEWHERE / SPEC_READING).

Limits of the instrument: the author and the judges are the same model family as the agents being
read; the 29/30 is agreement between two readings by that family, not human validation.

## Result

| Reason | library, items (n = 131) | library, one per run × risk (n = 83) | `bare` (n = 7) |
|---|---|---|---|
| SPEC_READING — the request did not ask for it / set no value / is read as excluding it | **63 (48%)** | **44 (53%)** | 5 |
| ELSEWHERE — belongs to another layer or task (mostly "no HTTP layer here, so the gateway") | 29 (22%) | 17 (20%) | 0 |
| DESIGN_DECISION — explicitly asks the user to choose | 20 (15%) | 9 (11%) | 2 |
| CANNOT — says it cannot be done with what it has | 8 (6%) | 4 (5%) | 0 |
| NOT_NEEDED — judges the control unnecessary or harmful here | 7 (5%) | 7 (8%) | 0 |
| VALUE_CHOICE — will not pick a number or policy value | 4 (3%) | 2 (2%) | 0 |
| NO_REASON | 0 | 0 | 0 |

42 of the 78 library runs with a hand-back contain at least one SPEC_READING. Reasons cluster by
case: `w18` (search rate limiting) is 14 of 19 ELSEWHERE — the fixture repo has no transport
layer, and agents say so; `w07` (CSV formula injection) is 10 of 15 DESIGN_DECISION, since the
usual fix changes what users see in the file; `w13` and `w08` are all NOT_NEEDED.

## Decision (rule fixed in PROTOCOL.md before labelling)

SPEC_READING is the largest library category and above 40% (48% of items, 53% deduplicated), so
**the next step is the completion gate**: one bounded Stop-hook repair that does not accept "the
request did not ask for it" as a reason. DESIGN_DECISION + ELSEWHERE is 37% (31% deduplicated),
below the 50% that would have made separating principle-2 decisions the first step — but large
enough that the gate's sentinel tasks must include a genuine design decision and a control that
really belongs elsewhere.

What this does **not** support: injecting default numbers (VALUE_CHOICE is 3%), or treating the
hand-backs as one population — `w18`'s ELSEWHERE and `w07`'s DESIGN_DECISION may be correct calls
on those fixtures, which a rule test cannot see.

## Files

- [`PROTOCOL.md`](PROTOCOL.md) — question, categories, decision rule, amendment 1.
- [`sample_ids.json`](sample_ids.json), [`author-labels.json`](author-labels.json) — the sample and its labels.
- [`reason-labels.jsonl`](reason-labels.jsonl) — one row per item: identity, reason, deciding quote.
  Final texts are not copied here; rebuild them with `tools/handback_items.py`.
