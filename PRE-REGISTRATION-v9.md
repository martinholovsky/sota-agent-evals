# Pre-registration v9 — FROZEN 2026-10-12, before any v9 run

**Why v9.** v7 showed that reading the cited rules files raises rule tests 0.698 → 0.868
(SUPPORTED). v8 showed that a hook asking agents to choose one or two files and read them in full
gets whole files read (79 → 472 lines per run) but the right file in only 11/20 runs, and rule
tests did not move (NULL) ([report](reports/2026-10-11-v8/REPORT.md)). Choosing by the prompt fails
too: a BM25 match of the prompt against the rules index found a cited file for 6/20 tasks.

Two questions from the operator on 2026-10-12, each answered with one arm, in **one invocation**:

1. **ROADMAP 73 (h): choose the file from the code the agent writes.** The prompt never names its
   risk ("export a CSV" never says formula injection), but the code does (`csv.writer`).
2. **Would linking from the first-depth file help?** In v8, of the 17 cited files a run never
   opened, a file the agent had read pointed at the right file *for the right topic* in only 3
   cases, and none of those pointers was followed. So the arm puts the same trigger table as
   links into the index every run loads (sota-python's `SKILL.md`, invoked in 20/20 v8 runs).

**The treatments.** SOTA-skills branch `roadmap-73-h` @ `52d1da0`:

- `scripts/code-rules-hook.py`. This is a PostToolUse hook on `Edit|Write|MultiEdit`. It matches
  the written text against a table of 19 triggers, then names each matching rules file's
  absolute path and the section to check, with one action: "Read each file named above in full
  now … then check this change against it". Each file is named at most once per session, and at
  most 2 new files per edit. Test files are skipped.
- `--table` renders the same 19 rows (23 file references) as a Markdown link table.

| arm | what it adds to `installed` |
|---|---|
| `installed+code` | the code-rules hook |
| `installed+linked` | v8's full-read depth hook, plus the table appended to the run's **copy** of `sota-python/SKILL.md` (the checkout is not edited) |

**The table was written after the cases were known.** It was written from the skills' rules
indexes, not from the cases, but its author had read all 20 tasks, so selection is in-sample. Its
offline recall was measured on 2026-10-12, before this file, by replaying every run's own
`Edit`/`Write` inputs in order through the hook: it named a cited file for:

| run set | cases with a cited file named | mean files named per run (max) |
|---|---|---|
| v7 `installed` | 17/20 | 2.35 (4) |
| v7 `bare` | 14/20 | 2.00 |
| v8 | 15/20 | 2.50 |

The bar, set before that replay, was ≥14/20 with a mean of ≤4.

The replay found three misses: an open redirect (w09), a wildcard turned into a regex (w12) and
API keys (w17). The table was **not** changed after the replay, so the measured arm does not fit
the misses it found. One more limit: a run that writes code through `Bash` only (v7's w17
`installed` run did) never fires the hook.

| pinned | value |
|---|---|
| case set | `cases-v4`, as v7 and v8 (git tree `33e4aa795f9a2e49d6893893f98c8193fe861e37`) |
| model, SDK, limits | as v7: `anthropic/claude-sonnet-5.5` via OpenRouter, `claude-agent-sdk==0.2.163`, 60 turns, $1.50, 1500 s, 1 sample per case, concurrency 4 |
| root | SOTA-skills `52d1da0`. Its `skills/` and `scripts/install.sh` are identical to v7's root `330bc4a` (`git diff 330bc4a 52d1da0 -- skills scripts/install.sh` is empty); router sha256[:16] `4e2540fca371fba7`. Its `skill-depth-hook.py` differs from v8's `8c48945` only in its docstring |
| treatment arms | `installed+code`, `installed+linked`: 40 runs, one invocation, interleaved case by case |
| controls | v7's 20 `installed` rows (primary and secondary) and v8's 20 rows (descriptive), reused, not re-run |
| harness | sota-agent-evals `3d9a425`, 144 tests |
| analysis | `python -m agent_evals.analyze --v9 runs.jsonl reports/2026-10-11-v7/runs.jsonl reports/2026-10-11-v8/runs.jsonl` |

**Reused controls.** The operator asked to keep paid runs few. v7's `installed` arm scored 37/53
on two separate days (2026-10-10 and 2026-10-11). Drift on the provider's side would still read as
an effect, and the report states this beside each verdict.

## Gates (any failure stops v9)

1. `preflight` PASS and `sandbox-probe` PASS against the root.
2. **Pilot**, case `w07` (a CSV export), both arms, never analysed. It passes if:
   - both rows have a transcript;
   - the `installed+code` row's transcript contains the hook's text naming
     `01-input-injection.md`;
   - the `installed+linked` row's transcript contains the table heading ("What your code does: the
     rules outside this skill") and v8's hook text.

## Validity, manipulation, decision rule (enforced by `analyze_v9`)

- **INVALID** if any of these holds:
  - more than one router across the three files;
  - an arm other than the two above in the v9 file;
  - any row whose prompt named rules files;
  - an `installed+code` row that received the depth hook's text or the table;
  - an `installed+linked` row that received the code hook's text;
  - any control row that received any treatment;
  - a valid row with no transcript;
  - an arm with no valid rows.
- **MANIPULATION FAILED** for a comparison if its marker reached fewer than 0.5 of the
  treatment's valid runs. The markers are the code hook's text for `installed+code`, and the
  table heading in the transcript for `installed+linked`.
- **Primary**: v7 `installed` → `installed+code`. **Secondary**: v7 `installed` →
  `installed+linked`. Each comparison uses v7's paired rule: pooled rule tests over the cases
  scored in both arms, with an exact one-sided sign-flip test over the per-case differences.
  - **SUPPORTED** iff p < 0.05 and the difference ≥ 0.09.
  - **NULL** iff the difference ≤ 0.02.
  - **INCONCLUSIVE** otherwise.
- The secondary does not qualify or replace the primary. No correction for multiple comparisons is
  applied.

## Descriptive, decided now (no verdict attached)

- v8 → `installed+linked`, paired the same way: the table alone, since both have v8's hook.
- Per arm: runs that opened a cited rules file (tool inputs), mean rules lines seen, mean cost and
  turns.
- Per case: rule tests across v7 `installed`, v7 named, v8 and both v9 arms.
- **Deferred, not omitted (ROADMAP 73 (g)).** In v7, w03 (SSRF), w06 (login throttling) and w18
  (rate limit) failed in every arm. The final messages of the library arms show the risk named and
  handed back ("please decide", "has to live at the gateway"). For those three cases, the report
  quotes each v9 run's final message on the topic. A rule test does not separate "flagged and
  deferred" from "never considered".

## Exclusions and budget

- Exclusions as v7.
- Credit read 2026-10-11 23:49 CEST: **$30.10**. The usage counter read $919.85 at 22:10 and
  $919.90 at 23:49, so it has settled.
- Expected cost: 40 runs at about $0.45–0.55 each (SDK), about $18–22, plus about $1.50 for gates
  and pilot. `--total-budget-usd 25`; the guard requires $25.

## Deviations

None yet.
