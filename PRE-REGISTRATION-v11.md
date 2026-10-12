# Pre-registration v11 — FROZEN 2026-10-12, before any v11 run

**Why v11.** v10's code-rules hook added a paragraph saying the named rules are part of the task,
to be built with a conservative default rather than handed back. Rule tests went 0.717 → 0.906
(SUPPORTED, [report](reports/2026-10-12-v10/REPORT.md)). The operator had proposed a simpler form,
used in other projects: mark the instruction "MANDATORY". [PRE-REGISTRATION-v10.md](PRE-REGISTRATION-v10.md)
decided that if v10 was SUPPORTED, a label-only arm would run next. This is that arm. It asks
whether the label alone does what v10's wording did.

**The treatment.** SOTA-skills branch `roadmap-73-j-label` @ `751a1a8`, a measurement root not meant
for merge. Its `scripts/code-rules-hook.py` is v10's (`a9d5865`) with the `APPLY` paragraph replaced
by one line:

```text
MANDATORY: apply the rules in each file named above to this change.
```

Nothing else differs. Like v9's hook, it does not say the rules are part of the task, does not
mention conservative defaults, and does not close the hand-back exit.

| arm | what it adds to `installed` |
|---|---|
| `installed+label` | the code-rules hook from the root above, installed exactly as v9's `installed+code` |

**What would refute it.**
- **Primary:** if the label alone is the lever, `installed+label` beats v9's `installed+code` by at
  least the bar. NULL (≤ 0.02) says a bare label adds nothing to the hook.
- **Secondary:** v10's wording against the label. SUPPORTED says the content of v10's paragraph
  matters beyond its emphasis. NULL says the label does as well.

| pinned | value |
|---|---|
| case set | `cases-v4` (git tree `33e4aa795f9a2e49d6893893f98c8193fe861e37`) |
| model, SDK, limits | as v10: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case |
| execution | as v10's deviation 1: two invocations of 10 cases (`w01`–`w10`, `w11`–`w20`), `--concurrency 2`, `--total-budget-usd 9` each |
| root | SOTA-skills `751a1a8`; `skills/` and `scripts/install.sh` identical to v7's root `330bc4a`; router `4e2540fca371fba7` |
| controls | v9's 20 `installed+code` rows (primary) and v10's 20 `installed+apply` rows (secondary), reused, not re-run |
| harness | sota-agent-evals `fbfd869`, 149 tests |
| analysis | `python -m agent_evals.analyze --v11 runs.jsonl reports/2026-10-12-v10/runs.jsonl reports/2026-10-12-v9/runs.jsonl` |

## Gates (any failure stops v11)

1. `preflight` PASS and `sandbox-probe` PASS against the root.
2. **Pilot**, case `w07`, never analysed. It passes if the row has a transcript containing the hook
   naming `01-input-injection.md` and the label, and **not** v10's wording.

## Validity, manipulation, decision rule (enforced by `analyze_v11`)

- **INVALID** if any of these holds:
  - more than one router across the three files;
  - an arm other than `installed+label` in the v11 file;
  - any row whose prompt named rules files;
  - an `installed+label` row that received v10's wording, the depth hook's text or the linked table;
  - a v9 or v10 row that carries the label;
  - a valid row with no transcript;
  - a group with no valid rows.
- **MANIPULATION FAILED** if the label reached fewer than 0.5 of the label arm's valid runs (primary),
  or v10's wording fewer than 0.5 of v10's (secondary).
- Both comparisons use v7's paired rule: pooled rule tests, with an exact one-sided sign-flip test
  over the per-case differences.
  - **SUPPORTED** iff p < 0.05 and the difference ≥ 0.09.
  - **NULL** iff the difference ≤ 0.02.
  - **INCONCLUSIVE** otherwise.

## Descriptive, decided now

- Spec-test passes per arm, as in v10.
- For every failing `installed+label` run, the final message on the tested topic, read three ways:
  built it, named it and left it out, or did not mention it.
- Per arm: cited rules files opened, rules lines seen, cost and turns.

## Budget

Credit read 2026-10-12 07:23 CEST: $25.14, with auto top-up. Expected cost: about $12 (SDK) for 20
runs plus about $0.75 for the gates and pilot.

## Deviations

None yet.
